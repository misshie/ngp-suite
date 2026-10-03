# GMDB データの mount 化（イメージからの分離）

作成日: 2026-10-03
状態: 設計（未実装）
対象リポジトリ: `ngp-suite`
作業ブランチ: `feat/mount-gmdb-data`（`main` = `ff5f994` / v0.2.0 から作成）

## 背景

v0.2.0 までは、GMDB 由来のモデル・ギャラリー・メタデータを `backend/data/` と
`backend/saved_models/` に置き、`docker compose build` でイメージに焼き込んでいた。
これらは個人情報を含み、配布もできないため、イメージ自体を共有できなかった。

本変更では、イメージにはコード・Python 依存・`mondo/`・`static/` だけを入れ、
GMDB データはユーザー手元のディレクトリを起動時に読み取り専用で bind mount する。
PII 境界を明確にすることが目的で、後続の Docker Hub 公開と Apple Silicon（linux/arm64）
対応の前提になる。

## 決定事項

1. ホスト側はリポジトリ外の親ディレクトリを推奨する。例: `~/ngpsuite-gmdb/{data,saved_models}`
2. 親ディレクトリは環境変数 `NGPSUITE_GMDB_DIR` で指定する。未設定時は `.`（`backend/` 自身）。
3. コンテナ内パスは現行どおり `/app/data` と `/app/saved_models`。Python のパス文字列は変更しない。
4. Dockerfile のデータ COPY は完全に削除する。焼き込みとの両対応はしない。データ変更で rebuild しない。
5. bind mount は読み取り専用（`:ro`）。Gallery Add は JSON ダウンロードのみで、書き戻しはない。
6. 起動前に必須ファイルを検査し、欠落を全件列挙して即座に終了する。
7. `README-be.md`（旧 v1.1.0）は変更しない。

## ホスト側ディレクトリ契約

```
$NGPSUITE_GMDB_DIR/
├── data/
│   ├── gallery_encodings/
│   │   └── GMDB_gallery_encodings_23052026_v1.1.4_service.pkl
│   ├── transformation_probabilities_07052025.csv
│   └── patient_metadata_2026-05-23_mondo.p
└── saved_models/
    ├── Resnet50_Final.pth
    ├── glint360k_r100.onnx
    ├── s1_glint360k_r50_512d_gmdb__v1.1.4_bs64_size112_channels3_last_model.pth
    └── s2_glint360k_r100_512d_gmdb__v1.1.4_bs128_size112_channels3_last_model.pth
```

`backend/.env.example` を用意し、利用者は `backend/.env` にコピーして編集する。
`backend/.env` は git 管理外にする。

```dotenv
NGPSUITE_GMDB_DIR=/absolute/path/to/ngpsuite-gmdb
```

既存ユーザーの移行は二通り。

- 推奨: データをリポジトリ外へ移し、`backend/.env` を作る
- 暫定: `backend/{data,saved_models}` に置いたまま `.env` を作らない（デフォルト `.` で mount される）

旧来の焼き込みイメージとビルドキャッシュにはデータが残るため、移行時に削除する
（`docker image rm backend-api:latest`、`docker builder prune`）。

## 必須ファイルの正本

実行時に実際に読むファイルだけを必須とする。

| ファイル | 読む場所 |
| --- | --- |
| `saved_models/Resnet50_Final.pth` | `lib/face_alignment.py`（顔検出） |
| `saved_models/s1_glint360k_r50_..._last_model.pth` | `lib/encode.py`（model 1） |
| `saved_models/s2_glint360k_r100_..._last_model.pth` | `lib/encode.py`（model 2） |
| `saved_models/glint360k_r100.onnx` | `lib/encode.py`（model 3） |
| `data/patient_metadata_2026-05-23_mondo.p` | `main.py` lifespan |
| `data/gallery_encodings/GMDB_gallery_encodings_23052026_v1.1.4_service.pkl` | `lib/evaluation.py` |
| `data/transformation_probabilities_07052025.csv` | `main.py`（PP4） |

- `glint360k_r50.onnx` は不要。学習用 `lib/models/my_arcface.py` のデフォルトで、Web API は読まない。README の必須リストから外す。
- `transformation_probabilities_*.csv` は現行コードでは欠落時に `{}` で黙って続行するが、PP4 に必要なので必須チェックに含める。
- `mondo/mondo-international.obo.gz` は患者データを含まない（CC BY 4.0）ため、従来どおりイメージに同梱する。

## 実装要点

1. `backend/Dockerfile`: `COPY saved_models/...` と `COPY data/...` を削除する。`CMD` は起動前チェックを通ってから uvicorn を起動する形にする。

   ```dockerfile
   CMD ["sh", "-c", "python -m lib.runtime_files && exec uvicorn main:app --host 0.0.0.0 --port 5000 --workers 2"]
   ```

2. `backend/.dockerignore`（新規）: `data/`、`saved_models/`、`.env` を除外し、誤ってビルドコンテキストに入らないようにする。
3. `backend/compose.yml`: `api` に long syntax の bind mount を 2 本追加する。

   ```yaml
       volumes:
         - type: bind
           source: ${NGPSUITE_GMDB_DIR:-.}/data
           target: /app/data
           read_only: true
           bind:
             create_host_path: false
         - type: bind
           source: ${NGPSUITE_GMDB_DIR:-.}/saved_models
           target: /app/saved_models
           read_only: true
           bind:
             create_host_path: false
   ```

   `create_host_path: false` により、パス指定ミスで空ディレクトリが作られず、compose がその場でエラーにする。
   `healthcheck` の `start_period: 90s` は維持し、`restart` は付けない。
4. `backend/lib/runtime_files.py`（新規）: 必須 7 ファイルが存在し、通常ファイルで、読めることを確認する。
   問題のあるファイルをすべて stderr に列挙し、`NGPSUITE_GMDB_DIR` と README の参照を促して `exit 1` する。
5. README.md / README-ja.md: 配置先を `$NGPSUITE_GMDB_DIR` に変え、`.env` 作成 → `docker compose build` → `docker compose up -d` の流れにする。
   データ更新は mount 元の差し替えと `docker compose restart api` だけでよいこと、破壊的変更と移行手順を明記する。

チェックを lifespan ではなく uvicorn 起動前に置くのは、`--workers 2` ではワーカー内の失敗が
再起動や healthcheck の待ち時間に埋もれやすいため。コンテナが即座に `exit 1` すれば、
`docker compose up` が依存失敗として直ちに報告し、nginx も起動しない。

## 確認

- GMDB データが無い状態で `docker compose build` が成功し、イメージの `/app` に `data` と `saved_models` が無い
- 存在しない `NGPSUITE_GMDB_DIR` を指定すると、`docker compose up` が bind source 不在で即座に止まる
- 一部のファイルが欠けると、api コンテナが欠落一覧を出して exit 1 になり、nginx は起動しない
- 正しく mount すると `Load MONDO index: 58942 terms ...` が出て、`/api/status` と `/api/predict`（HPO の有無の両方）が v0.2.0 と同等に動く
- コンテナ内で `/app/data` に書き込めない（`:ro`）

## 今回やらないこと

- Docker Hub への公開（タグ付け・CI）
- linux/arm64（Apple Silicon）イメージ。Docker 内では MPS が使えないため、CPU 推論前提になる
- CUDA 推論の有効化（`USE_CUDA` ビルド引数は現状維持）
- `config.json` の認証情報がイメージに焼き込まれる問題（Hub 公開前に環境変数か mount へ移す）
- `README-be.md` と `gmdb-mondo` の変更
