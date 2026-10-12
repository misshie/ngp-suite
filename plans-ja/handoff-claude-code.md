# 引き継ぎメモ（Claude Code 向け）

更新日: 2026-10-12
対象: v0.3.0（`feat/mount-gmdb-data` を `main` にマージしたリリース）と、その後の作業ブランチ `feat/mondo-distance-api`（未マージ）。リリース手順は [release-v0.3.0.md](release-v0.3.0.md) を参照。

この文書は公開リポジトリにあります。認証情報、ローカルのパス、患者データの詳細は書かないでください。

## 1. 現在の到達点

v0.2.0 で、ギャラリーの疾患の同一性を OMIM から MONDO に移しました。v0.3.0 では、配布と運用の方式を変えました。

- GMDB データをイメージに焼き込まず、`NGPSUITE_GMDB_DIR` から読み取り専用で mount する（[feature-mount-gmdb-data.md](feature-mount-gmdb-data.md)）
- 認証情報を環境変数から読み、公開先を既定で 127.0.0.1 にする（[feature-auth-env.md](feature-auth-env.md)）
- 第三者ライセンス表示を追加する（[feature-third-party-notices.md](feature-third-party-notices.md)）
- メタデータ pickle の生成スクリプトを `tools/gmdb-mondo/` に公開する
- README のモデル・データ節を整理し、PP4 がこの版では利用できないことを明記する

### 作業中: `feat/mondo-distance-api`（push 済み、`main` へのマージは保留）

2 つの MONDO ID の間の is_a 経路の長さを返す API を追加した（[feature-mondo-distance.md](feature-mondo-distance.md)）。バックエンドだけの変更で、Docker での動作確認は済んでいる。

- `GET /api/mondo/distance?id1=…&id2=…` を `/api/predict` と同じ Basic 認証で保護する
  - ID の形式が不正なら 422、OBO にない ID（廃止済みを含む）なら 404 を返す
- 距離は最も近い共通祖先（LCA）を経由する経路だけで数える
  - 経路ごとのエッジ数を `distance`（昇順）で返し、その最小値を `minimum` で返す
  - LCA ごとの内訳を `common_ancestors` で返す
- 実装は `backend/lib/mondo.py` の `mondo_distance()`。`main.py` は MONDO の索引を `_mondo_index` としてグローバルに保持するようになった
- README と README-ja の認証の節に、このエンドポイントを書き加えた
- PR は未作成。マージするときは、CLAUDE.md の規約どおりマージコミットで取り込み、ブランチを残す

## 2. 残作業（推奨順）

1. `feat/mondo-distance-api` の PR の作成と `main` へのマージ（メンテナの判断待ち）
2. 再生成した pickle（非ヒト MONDO 用語を除外した版）を読み込んだ状態で、実機確認する
   - 解析を 1 件実行し、SYNDROMES / GENES / PATIENTS の各タブと外部リンクを確認する
   - cattle や dog などの非ヒト疾患が候補に出ないことを確かめる
3. Docker Hub への公開（タグ付けと CI）
4. Apple Silicon（linux/arm64）向けのイメージ。CPU 推論が前提
5. CUDA 推論の有効化
6. `/api/encode` と `/api/crop` への認証の追加
7. 再配布ライセンスの確認。イメージは CC-BY-NC-4.0 で、insightface のモデルは非商用の研究目的に限られる
8. `README-be.md` の更新
9. 優先度の低い項目
   - Patients タブの病名を MONDO ラベルにする
   - 列ヘッダの多言語対応（いまは Columns ボタンの文言だけ）
   - PP4 と `transformation_probabilities_*.csv` の再設計
     - MONDO 版の pickle には PP4 の閾値がないので、全症候群が "Not available yet" になる
     - CSV のキーは GMDB の疾患名で、MONDO の疾患名とは一致しない

## 3. ハマりどころ

- **`tools/gmdb-mondo/` はコピー:** 正本は別の非公開リポジトリにあり、こちらへは手動で同期する。こちらだけを直さないこと
- **`020_…py` はラッパー:** 本体は `map_GMDBomim_to_mondo.py`。Python は数字で始まるモジュール名を import できないので、本体の名前を変えない
- **ROBOT の一時ファイル:** `mktemp` が 0600 で作るので、Docker 内の ROBOT が読めない。`010_…sh` が `chmod a+r` で対処している
- **自己署名 HTTPS:** Cursor の埋め込みブラウザでは `https://localhost/` を開けない。通常のブラウザで確認する
- **macOS の 443 番ポート:** 127.0.0.1:443 で公開するには、Docker Desktop の "Allow privileged port mapping" が必要。使えなければ `NGPSUITE_PORT=8443` にする
- **`backend/static/` のノイズ差分:** `./build-frontend.sh` を実行すると、フォント preload の並び順だけが変わることがある。意図した変更だけをコミットする
- **複数 MONDO の意味は 2 種類:** 重複診断（GMDB に複数の OMIM）と、遺伝子由来の多義性。`mondo_source` で区別する
- **is_a の source 注記は別経路ではない:** OBO の 1 本の is_a に `source=` が複数付くことがある（例: MONDO:0007336 → MONDO:0016064）。エッジは 1 本として数える
- **`ngpsuite-backend-scheme.json` は `/api/predict` 専用:** 応答のスキーマはこのエンドポイントのものだけ。`/api/mondo/distance` の応答の形は設計メモに書いてある
- **ローカルでは `main.py` を import できない:** ホストの Python には FastAPI や torch がない。`lib/mondo.py` の関数は `python3 -I` で同梱の OBO を読んで試せるが、エンドポイントは Docker で確認する

## 4. 主要ファイル

- バックエンド: `backend/main.py`、`backend/lib/{mondo,evaluation,integrator,pubcasefinder,runtime_files,auth_config}.py`
- Docker: `backend/Dockerfile`、`backend/compose.yml`、`backend/.env.example`
- API の契約: `backend/ngpsuite-backend-scheme.json`
- フロント: `frontend/src/components/Results.vue`、`frontend/src/stores/app.ts`
- 設計メモ: `plans-ja/feature-*.md`
