# 引き継ぎメモ（Claude Code 向け）

更新日: 2026-10-14
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

2 つの MONDO ID を比べる API を追加した。バックエンドだけの変更で、Docker での動作確認は済んでいる。
設計メモは [feature-mondo-distance.md](feature-mondo-distance.md)（最初の版）と [feature-mondo-ic-similarity.md](feature-mondo-ic-similarity.md)（現在の仕様）。

- `GET /api/mondo/distance?id1=…&id2=…` を `/api/predict` と同じ Basic 認証で保護する
  - ID の形式が不正なら 422、OBO にない ID（廃止済みを含む）なら 404 を返す
- intrinsic IC による Resnik / Lin 類似度を返す
  - 既定は Seco の IC で、範囲は human disease（MONDO:0700096）の子孫
  - `ic_method`（`seco` | `descendants`）と `ic_root` で変えられる
- MICA までのホップ数を `mica.hops = [id1 側, id2 側]`（最短経路）で返す
  - 最初の版の `distance`（LCA 経由の全経路長）と `minimum` は、メンテナの判断で廃止した
- `common_ancestors` は最も近い共通祖先の一覧で、各項目に `ic` と `hops` が付く
- 実装は `backend/lib/mondo.py` の `build_ic_table()` と `mondo_similarity()`
  - `main.py` は MONDO の索引を `_mondo_index` として、子孫数を `_mondo_ic`（メモリのみ）として保持する
- README と README-ja に「6. MONDO の距離と類似度の API」の節がある
- 単体テストは `backend/tests/`（unittest）にある。Docker での動作確認も済んでいる
- PR は未作成。マージするときは、CLAUDE.md の規約どおりマージコミットで取り込み、ブランチを残す

#### コミットの状況（2026-10-14 時点）

- `35f1617` まで push 済みで、未コミットの変更はない
- 経緯
  - `eb6067d`: IC 類似度の最初の版。既定は `descendants` で、`distance` と `minimum` を残していた
  - `35f1617`: Seco の IC を既定にし、ホップ数を `mica.hops` に置き換えた。README、設計メモ、テストも更新した

#### 検証用の値（Seco、範囲 MONDO:0700096、同梱 OBO 2026-09-01）

| id1 | id2 | MICA | hops | Resnik | Lin |
|---|---|---|---|---|---|
| MONDO:0007843 Kabuki syndrome 1 | MONDO:0016512 Kabuki syndrome | MONDO:0016512 | [1, 0] | 0.8907 | 0.9422 |
| MONDO:0007843 Kabuki syndrome 1 | MONDO:0010465 Kabuki syndrome 2 | MONDO:0016512 | [1, 1] | 0.8907 | 0.8907 |
| MONDO:0007843 Kabuki syndrome 1 | MONDO:0008678 Williams syndrome | MONDO:0002254 syndromic disease | [2, 1] | 0.1927 | 0.1927 |
| MONDO:0008678 Williams syndrome | MONDO:0008608 Down syndrome | MONDO:0020049 autosomal anomaly | [4, 2] | 0.3928 | 0.4460 |
| MONDO:0012371 Noonan syndrome 3 | MONDO:0013186 Noonan syndrome 6 | MONDO:0018997 Noonan syndrome | [1, 1] | 0.7306 | 0.7306 |
| MONDO:0012371 Noonan syndrome 3 | MONDO:0018997 Noonan syndrome | MONDO:0018997 | [1, 0] | 0.7306 | 0.8444 |
| MONDO:0016512 Kabuki syndrome | MONDO:0018997 Noonan syndrome | MONDO:0019042 multiple congenital anomalies/dysmorphic syndrome | [2, 2] | 0.3271 | 0.4035 |

- NS3 と NS6 は、KS1 と KS2 と同じく総称の 1 段下の病型どうしだが、Lin は 0.7306 と 0.8907 で違う。Noonan syndrome の総称は病型が多く、IC が低いため
- Kabuki と Noonan の組では、MICA（2 段上の MONDO:0019042）が最短ホップの LCA（1 段上の syndromic disease）と一致しない

#### 検討中: 「おおむね正解」の判定（id1 = 診断候補、id2 = 正しい診断）

Lin の閾値に定説はない。固定閾値（例: Lin ≥ 0.8）には次の弱点がある。
- 総称の広さで値が変わる。Lin ≥ 0.8 では、NS3 と NS6 の組だけが外れる
- MONDO の版や範囲のルートで値が変わる
- Lin は対称なので、粗い候補と隣の病型とを区別できない

代わりの案として、構造で判定することを提案した（メンテナの判断待ち）。
1. 完全一致: id1 = id2
2. おおむね正解: MICA が臨床的な疾患単位で、かつ hops がいずれも 1 以下（上限は要決定）
   - 臨床的な疾患単位とは、`xref: OMIMPS:…`（equivalentTo）か、`subset: ordo_disorder` を持つ用語
   - 例: Kabuki syndrome は OMIMPS:147920 と Orphanet:2322、Noonan syndrome は OMIMPS:163950 と Orphanet:648
3. 不正解: MICA が分類用の用語（`subset: disease_grouping` や `ordo_group_of_disorders`）。例: MONDO:0019042

- Lin は合否の判定に使わず、連続値の副次指標として報告する
- Lin の閾値がどうしても要る場合は、臨床医が判定した組の集合から ROC 曲線などで決め、MONDO の版と範囲のルートとあわせて報告する

実装するなら、次の 2 点が必要になる。
- `load_mondo_index` で OMIMPS の xref と `subset` を読む
- API で、MICA が臨床的な単位かどうかに印を付ける

## 2. 残作業（推奨順）

1. `feat/mondo-distance-api` の作業の続き（メンテナの判断待ち）
   - 「おおむね正解」の構造的な判定を実装するかどうかを決める（上記の検討中の節）
   - PR を作成し、`main` へマージする
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
- **is_a の source 注記は別経路ではない:** OBO の 1 本の is_a に `source=` が複数付くことがある（例: MONDO:0007336 → MONDO:0016064）。`load_mondo_index` は親を集合にしているので、エッジは 1 本になる
- **`ngpsuite-backend-scheme.json` は `/api/predict` 専用:** 応答のスキーマはこのエンドポイントのものだけ。`/api/mondo/distance` の応答の形は設計メモに書いてある
- **ローカルでは `main.py` を import できない:** ホストの Python には FastAPI や torch がない。`lib/mondo.py` の関数は `python3 -I` で同梱の OBO を読んで試せるが、エンドポイントは Docker で確認する。`backend/tests/` の単体テストは `lib/mondo.py` だけを import するので、ホストで実行できる

## 4. 主要ファイル

- バックエンド: `backend/main.py`、`backend/lib/{mondo,evaluation,integrator,pubcasefinder,runtime_files,auth_config}.py`
- Docker: `backend/Dockerfile`、`backend/compose.yml`、`backend/.env.example`
- API の契約: `backend/ngpsuite-backend-scheme.json`
- フロント: `frontend/src/components/Results.vue`、`frontend/src/stores/app.ts`
- 設計メモ: `plans-ja/feature-*.md`
