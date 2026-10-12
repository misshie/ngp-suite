# v0.3.0 のリリース手順

作業ブランチ: `feat/mount-gmdb-data`（`main` = `ff5f994` / v0.2.0 から作成）
方式: PR #5 / v0.2.0 と同じ。マージコミットで取り込み、ブランチは残す。`main` に `v0.3.0` タグを付け、`gh release` でノートを作る。
バージョン番号を書いたファイルはないので、番号の更新はしない。

## 手順

1. 引き継ぎ文書（`CLAUDE.md`、`plans-ja/handoff-claude-code.md`、この文書）をコミットして push する
2. `gh pr create --base main --head feat/mount-gmdb-data` で PR を作る
3. `gh pr merge --merge` でマージする（`--delete-branch` は付けない）
4. `gh release create v0.3.0 --target main --title v0.3.0 --notes-file <リポジトリ外の一時ファイル>`
5. タグが `main` のマージコミットを指していることと、ローカルの `main` が最新であることを確認する

## 破壊的変更（PR とリリースノートの冒頭に書く）

- GMDB データをイメージに含めなくなった。`backend/.env` の `NGPSUITE_GMDB_DIR` で `data/` と `saved_models/` の親ディレクトリを指定し、読み取り専用で mount する。必須ファイル 7 個を起動前に検査し、不足があれば列挙して停止する
- `backend/config.json` を廃止した。認証情報は `NGPSUITE_USERNAME` / `NGPSUITE_PASSWORD` で渡す。未設定なら placeholder を使い、起動時に警告する
- 公開先が既定で `127.0.0.1` になった（`NGPSUITE_BIND`、`NGPSUITE_PORT`）。macOS で 443 番ポートを使うには Docker Desktop の "Allow privileged port mapping" が必要
- `glint360k_r50.onnx` が不要になった
- 移行: データを焼き込んだ旧イメージとビルドキャッシュを削除する。手順は README の "Upgrading from v0.2.0 or earlier" を参照

## そのほかの変更

- `tools/gmdb-mondo/`: MONDO でキー付けしたメタデータ pickle の生成スクリプト（GMDB 運営者向け）
- `backend/THIRD_PARTY_NOTICES.md`: 第三者ライセンス表示
- README のモデル・データ節を再構成し、PP4 がこの版では利用できないことを注記した
- `plans-ja/` に設計メモと Claude Code 向けの引き継ぎ文書を追加した

## リリースノートの構成（v0.2.0 と同じ）

- Highlights と、PR へのリンク
- Breaking changes と移行手順
- What is new
- Attribution（Mondo Disease Ontology、CC BY 4.0）

README へのリンクは `https://github.com/misshie/ngp-suite/blob/v0.3.0/README.md` にする。
