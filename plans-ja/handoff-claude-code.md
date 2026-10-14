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
設計メモは [feature-mondo-distance.md](feature-mondo-distance.md)（最初の版）、[feature-mondo-ic-similarity.md](feature-mondo-ic-similarity.md)（現在の仕様）、[feature-mondo-match-level.md](feature-mondo-match-level.md)（一致度の判定。設計中）。

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

- この引き継ぎメモの更新まで push 済みで、未コミットの変更はない
- 経緯
  - `eb6067d`: IC 類似度の最初の版。既定は `descendants` で、`distance` と `minimum` を残していた
  - `35f1617`: Seco の IC を既定にし、ホップ数を `mica.hops` に置き換えた。README、設計メモ、テストも更新した
  - `69d1250`: 疾患単位による一致度の判定の設計メモを追加した（コードの変更はない）

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

#### 設計中: 疾患単位による一致度の判定（未実装、臨床医の判定待ち）

設計メモは [feature-mondo-match-level.md](feature-mondo-match-level.md)。Lin の固定閾値には定説がなく、総称の広さや MONDO の版で値が変わるため、構造で判定する。Lin は連続値の副次指標として報告する。

- 疾患単位: `xref: OMIMPS:…`（equivalentTo）か `subset: ordo_disorder` を持ち、`disease_grouping` と `ordo_group_of_disorders` を持たない用語
  - 各用語は、自分自身を含めて最も近い疾患単位に引き上げる（病型 → 総称）
- 判定（4 段階、API は対称な判定だけを返す）
  1. 完全一致
  2. 同一疾患単位。包含（総称と病型）と隣の病型を区別しない。ギャラリーには総称までしか診断のない古い症例があるため（メンテナの判断）
  3. 関連疾患群。疾患単位どうしの MICA までの hops がいずれも 1 以下で、かつ MICA が許可リストにある（案 B'）
  4. 不正解
- 生の hops では判定できない。NS3 と CFC1、Kabuki と Noonan は、どちらも [2, 2]。疾患単位にそろえると、前者は [1, 1]、後者は [2, 2] になる
- 許可リスト（案 B'、メンテナが選択）
  - hops だけでは 3 が広すぎる（Kabuki と Williams も [1, 1]）。子孫数の上限だけでは閾値がもろい（MONDO:0020297 は 29、RASopathy は 37）
  - 子孫数 50 以下の候補を臨床医が判定する。候補は現行の定義で 94 個、改訂案で 104 個
  - 判定基準（基準 1）: 「この群に属する疾患は、顔貌を含む臨床像が互いに似ていて、互いに鑑別診断に挙がるか」
  - 候補の一覧（TSV と CSV）、生成スクリプト、判定の手引きは、ギャラリー由来の情報を含むので、リポジトリの外に置いた。リポジトリには入れない
- 未決定の点
  - 子孫数 50 以上の疾患単位を単位とみなさないこと（intellectual disability, autosomal dominant などに 63 用語が集まるため）
  - 疾患単位の祖先がない用語（ギャラリーの約 22%）を、自分自身の単位とみなすこと
- ギャラリーの集計は、v1.1.4 の pickle の OMIM ID を Stage 2 の関数で MONDO に写した近似（1,091 疾患のうち 899 疾患）
  - MONDO 版 pickle は `NGPSUITE_GMDB_DIR` になかった
  - ホストに numpy がないので、pickle は numpy の型を代用品に置き換えて読んだ

## 2. 残作業（推奨順）

1. `feat/mondo-distance-api` の作業の続き
   - 臨床医による許可リストの判定を待つ（上記の設計中の節）
   - 未決定の 2 点（広すぎる疾患単位、疾患単位のない用語）を決める
   - 疾患単位による判定を実装する。`load_mondo_index` で OMIMPS と `subset` を読み、許可リストは `backend/mondo/` に置く
   - MONDO 版 pickle が手に入ったら、ギャラリーの集計と候補の一覧を作り直す
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
