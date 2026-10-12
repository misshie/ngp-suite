# 認証情報の環境変数化とポート公開範囲の既定変更

作成日: 2026-10-04
状態: 実装済み・検証済み（2026-10-04）
対象リポジトリ: `ngp-suite`
作業ブランチ: `feat/auth-env`（`feat/mount-gmdb-data` から作成）
先行する設計: [feature-mount-gmdb-data.md](feature-mount-gmdb-data.md)

## 背景

`backend/config.json` の認証情報（Basic 認証の `username` / `password`）が `COPY` でイメージに入り、
`main.py` が起動時に読んでいた。リポジトリ内の値はプレースホルダだが、利用者が値を変えると
その値がイメージの層に残る。GMDB データの mount 化（先行設計）で、データがイメージから分離された。
認証情報も同じ考え方で、イメージの外から渡す。

また、`compose.yml` の `"443:443"` は全インターフェースに公開されるため、LAN 公開が既定になっていた。

## 前提とする利用範囲

- 利用は localhost と LAN まで。インターネット公開は想定しない。
- `/api/predict` の応答には GMDB 由来の患者情報（`subject_id`、`image_id`、遺伝子など）が含まれる。
- フロントの初期値は `your_username` / `your_password` で、リポジトリ・README・フロントに公開されている。
  プレースホルダのままの Basic 認証は、実質的に認証なしと同じ。

## 決定事項

1. プレースホルダのままでも**起動する**。警告を出すだけで、起動は止めない。変更はどうしても必要な人だけが行う。
2. 認証情報は環境変数 `NGPSUITE_USERNAME` / `NGPSUITE_PASSWORD` で渡す。未設定または空文字ならプレースホルダを使う。
3. 443 の公開アドレスは `NGPSUITE_BIND`（既定 `127.0.0.1`）で決める。LAN に出す人だけが `0.0.0.0` に変える。
4. 警告は uvicorn 起動前に 1 回だけ出す（`python -m lib.auth_config`。ワーカー 2 本の import 時には出さない）。
5. `config.json` はイメージにもリポジトリにも置かない。
6. 公開するホスト側ポートは `NGPSUITE_PORT`（既定 443）で変えられる。実装中に判明した下記の制約への対応（後述）。
7. `/api/encode` と `/api/crop` への認証追加は今回しない。GMDB のデータを返さず、LAN 前提でのリスクが低いため。

## メッセージ

`python -m lib.auth_config` は常に `exit 0`。

| 認証情報 | `NGPSUITE_BIND` | 出力 |
| --- | --- | --- |
| プレースホルダのまま | ループバック（`127.0.0.1` / `::1` / `localhost`） | 注意を 1 行（認証は実質無効。README の Authentication 節を参照） |
| プレースホルダのまま | ループバック以外 | 強い WARNING（LAN 上の誰でも `/api/predict` を呼べ、応答に GMDB 由来の患者情報が含まれる。変更方法を示す） |
| 変更済み | 任意 | 何も出さない |

nginx の起動メッセージ（`confirm-startup.sh`）には静的な 1 行だけを足す。nginx にパスワードは渡さないため、
既定かどうかの判定はそこでは行わず、判定付きの警告は `docker compose logs api` に出る。

## 実装要点

1. `backend/lib/auth_config.py`（新規）: `load_credentials()`、`is_default()`、`is_loopback()`、警告出力の `main()`。
2. `backend/main.py`: `config.json` の読み込みを `load_credentials()` に置き換える。`secrets.compare_digest` は維持。
3. `backend/Dockerfile`: `COPY config.json` を削除し、`CMD` を `runtime_files` → `auth_config` → uvicorn の順にする。
4. `backend/config.json`: 削除する（他に読むコードが無いことを確認済み）。`README-be.md` の記述は旧版のままで触らない。
5. `backend/compose.yml`: `api.environment` に 3 変数を追加し、nginx の `ports` を `"${NGPSUITE_BIND:-127.0.0.1}:${NGPSUITE_PORT:-443}:443"` にする。
   nginx にも `NGPSUITE_PORT` を渡し、起動バナーの URL（`https://localhost[:ポート]`）にだけ使う。
6. `backend/.env.example`: 3 変数を説明付きで追記する。
7. README.md / README-ja.md: Authentication 節、破壊的変更の注記、`.env` の新変数。
   Web UI の Settings にも同じ認証情報を入れる必要があることを明記する。

## 破壊的変更

- 443 の既定が localhost のみになる。LAN で使っていた人は `backend/.env` に `NGPSUITE_BIND=0.0.0.0` を設定する。
- `config.json` は使われなくなる。値を変えていた人は `.env` に移し、再ビルドする。

## 確認

- イメージの `/app` に `config.json` が無い
- 既定のまま起動: ポートが `127.0.0.1:443`、ログに注意が 1 行、既定の認証で `/api/predict` が通る
- 独自の認証情報で起動: 警告が出ず、既定の認証は 401、独自の認証は 200
- `NGPSUITE_BIND=0.0.0.0` で認証情報は既定: ポートが `0.0.0.0:443`、強い WARNING、起動は止まらない
- GMDB ファイル欠落時は `runtime_files` が先に止まる（先行設計の挙動を維持）

## macOS の特権ポート（実装中に判明）

macOS は 1024 未満のポートを、全アドレス（`0.0.0.0`）なら一般ユーザーでも bind できるが、`127.0.0.1:443` のような
個別アドレスには特権が要る。Docker Desktop for Mac では特権ヘルパー（vmnetd）が無いと、
`failed to connect to /var/run/com.docker.vmnetd.sock` で nginx が起動に失敗する（実機で確認）。

対応:

- 既定の `127.0.0.1:443` は維持する（URL は従来どおり `https://localhost`）。
- Docker Desktop の **Settings > Advanced > Allow privileged port mapping** を有効にする手順を README に書く。
- 有効にできない人向けに `NGPSUITE_PORT=8443` のような特権の要らないポートを選べるようにする。`127.0.0.1` に限定したまま使える。
- Linux と Windows では不要。

## 検証結果（2026-10-04）

GMDB データはリポジトリ外の `NGPSUITE_GMDB_DIR`、画像は `backend/demo_images/cdls_demo.png`。
応答 JSON はファイルに保存し、キーの有無だけを確認した。

| 項目 | 結果 |
| --- | --- |
| `docker compose build`、イメージの `/app` | 成功。`config.json` は無い |
| 既定のまま起動 | ポートは `127.0.0.1:443`。`api` のログに NOTICE が 1 行。nginx のバナーに認証の案内。既定の認証で `/api/predict` が 200（`mondo_version`・`mondo_id`・`ACMG_PP4` あり） |
| 独自の認証情報で起動 | NOTICE・WARNING なし。既定の認証は 401、独自の認証は 200 |
| `NGPSUITE_BIND=0.0.0.0` + 既定の認証 | ポートは `0.0.0.0:443`。WARNING が出るが、`api` は起動して healthy |
| `NGPSUITE_PORT=8443` | ポートは `127.0.0.1:8443`。バナーは `https://localhost:8443`。`/api/predict` が 200 |
| GMDB ファイル欠落（空のディレクトリ） | `api` が 7 件すべてを列挙して exit 1。nginx は `Created` のまま。認証メッセージは出ない（`runtime_files` が先に止まる） |
| 特権ヘルパー無しの `127.0.0.1:443` | vmnetd のエラーで nginx が起動せず（実機で再現）。設定を有効にすると起動する |

## 今回やらないこと

- Docker Hub への公開、タグ、CI
- linux/arm64（Apple Silicon）イメージ
- `/api/encode`・`/api/crop` への認証追加
- 再配布ライセンスの確認（Hub 公開前に別途）
- `README-be.md` の更新
