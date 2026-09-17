# MONDO ベースの症候群ランキング（フェーズ2）

実施日: 2026-09-17
ブランチ: `feat/update-backend-gm-1.1.4-mondo`（`feat/update-backend-gm-1.1.4-ExportFeatVecMeta` から分岐）

GestaltMatcher バックエンドはギャラリー疾患の同一性を OMIM ID（実際には OMIM ID ないし
Phenotypic Series ID）で管理していた。これを MONDO Disease Ontology の用語に置き換え、
選ばれた疾患の上位概念（親・祖父母）も併せて表示するようにした。

## なぜ MONDO に移すのか

OMIM は疾患のサブタイプに番号を振るが、サブタイプ間の上位・下位関係を機械可読な形では
持たない。従来はこれを補うために `internal_syndrome_id` / `internal_syndrome_name` という
人手のグルーピングを持っていた（"Kabuki Syndrome Type 1/2" に対する "Kabuki Syndrome" の
ような対応付け）。MONDO は `is_a` 階層を持つので、この人手の対応表は不要になる。

副次的な利点として、PubCaseFinder との突き合わせキーが増える。MONDO を主キーにした場合、
HPO 3語のクエリで返る 1,603 症候群のうち 1,396 件（87.1%）に PubCaseFinder の rank が付いた。
OMIM 単独のときは 974 件だった。

## 入力データ

`backend/data/` に2ファイルを配置する（`.gitignore` 対象。Docker イメージには焼き込む）。

| ファイル | 内容 |
| --- | --- |
| `patient_metadata_2026-05-23_mondo.p` | ギャラリーのメタデータ。`disorder_level_metadata` の各画像が `mondo_id: list[str]` と `mondo_source` を持つ |
| `mondo-international.obo.gz` | MONDO リリース（8.5 MB、58,517 用語）。用語ラベルと `is_a` 階層の解決に使う |

生成手順は別リポジトリ `gmdb-mondo`（患者メタデータを含むため private）にある。
MONDO は CC BY 4.0 で再配布可能、患者データを含まないため Docker イメージに同梱している。

pickle 側の主な数値: 採用画像 17,566 枚、`mondo_id` を持つ 17,282 枚（98.4%）、
distinct MONDO ID 1,560 語、`mondo_id` を2つ以上持つ画像 739 枚。

## 実装

### `backend/lib/mondo.py`（新規）

OBO を gzip 透過で読み、`{mondo_id: {"name", "parents"}}` を構築する。起動時1回、実測約2秒。

- `load_mondo_index(path)` — `is_obsolete: true` のスタンザは完全にスキップする。廃止用語も
  旧来の xref を保持しているため、残すと後継の現行用語を覆い隠す
- `resolve(index, mondo_id)` — ラベル、親、祖父母を返す。祖父母は親の親を集合化し、自身と
  親集合を除外した上で MONDO ID 昇順に並べる。MONDO は多重継承を許すため、除外しないと
  同じ用語が親と祖父母の両方に現れる
- `build_syndrome_index(metadata, mondo_index)` — ギャラリーを症候群候補に展開する。
  各候補は安定した文字列キーを持ち、MONDO があれば `MONDO:0008678`、無ければ
  `GMDB:<disorder_internal_id>` になる

`is_a` 行は `is_a: MONDO:0002254 {source="DOID:1928"} ! syndromic disease` のように修飾子が
入りうるので、`!` で切るのではなく最初の空白区切りトークンを取る。

### 1画像が複数の症候群を支持する場合

ギャラリー画像が複数の `mondo_id` を持つ状況は2通りある。

1. GMDB に重複診断が記録されている（例: 画像 341 は `omim_ids: "122470, 194050"` で
   Cornelia de Lange 症候群1型と Williams 症候群の両方）
2. OMIM ID が無く遺伝子シンボルから解決したため、その遺伝子が起こしうる疾患が複数出た

どちらも「同じ顔貌が複数の疾患を支持している」ことに変わりはないので、`get_first_synds()` を
`get_first_genes()` と同形にし、画像ごとの内側ループで候補キーを積むようにした。結果として
同一 `image_id` かつ同一 `distance` の行が複数並ぶ。

### 遺伝子由来の候補の扱い

遺伝子経由で解決した候補セットは臨床的に不均一になる。`PDGFRB` は乳児筋線維腫症・特発性
基底核石灰化症4・過成長症候群を返すし、これらはすべて同じ gestalt distance を持つため、
顔貌類似度としての識別情報を持たない。

そこで2つの扱いを入れた。

- `format_syndrome_json()` の末尾で `(distance, mondo_source != 'omim')` による安定ソートを
  かけ、同一距離では OMIM 由来を先に置く
- レスポンスに `mondo_source` を残し、フロントで「遺伝子由来」のチップを付ける

候補数に上限を設けて切り捨てる案は採らなかった。閾値に原理的根拠が無いのと、表示上の問題を
データを捨てて解くのは方向が逆であるため。HPO を入力した場合は PubCaseFinder による
meta ranking が同点クラスタを分離する。

### MONDO に載らない疾患

284 枚（48 グループ）は MONDO に疾患エントリ自体が存在しない遺伝子（`PSMC3`, `SPATA5`,
`KCTD3` など）で、これはデータ側の限界である。これらを落とすと gestalt 上位が消えてしまう
ので、`GMDB:<disorder_internal_id>` をキーに GMDB 側の `disorder_name` で一覧に出す。
MONDO 列は空、`mondo_source` は `null` になる。

### PubCaseFinder

`target=omim` のレスポンスに既に `mondo_id` が含まれているので、追加リクエストは要らない。
`integrator.py` に `pcf_by_mondo` を追加し、複数の OMIM エントリが同一 MONDO を指す場合は
最小 rank を採る。突き合わせは `mondo_id` を優先し、無いときだけ従来の `pcf_by_omim` に
落ちる。患者リストと遺伝子リストの突き合わせは変更していない。

### ACMG PP4

新 pickle に PP4 閾値キーが1件も無いため、`get_pp4()` は変更せずに全行
`("", "Not available yet")` を返す。列は将来のために残してある。

### 遺伝子タブ・患者タブ

`format_gene_json()` と `format_subject_json()` は `gene_level_metadata` を参照しており、
新 pickle でも同じ形なので変更していない。

1点だけ記録しておく。遺伝子名が無いレコードに疾患名を擬似遺伝子として割り当てる既存の慣習が
旧 pickle の 70 件から新 pickle では 232 件に増える。旧 pickle からの継承挙動で今回のスコープ
外だが、遺伝子タブに疾患名が混じる件数が増える。

## 変更ファイル

| ファイル | 内容 |
| --- | --- |
| `backend/lib/mondo.py` | 新規。OBO パース、親・祖父母解決、症候群候補索引 |
| `backend/main.py` | 新 pickle と OBO のロード、`build_syndrome_index()` の呼び出し |
| `backend/lib/evaluation.py` | `get_first_synds()` の複数候補対応、`format_syndrome_json()` の MONDO フィールドと同一距離ソート |
| `backend/lib/integrator.py` | `pcf_by_mondo` の追加 |
| `backend/Dockerfile` | 新 pickle と OBO の COPY |
| `backend/ngpsuite-backend-scheme.json` | `syndromeEntry` に MONDO 系フィールド、`mondoTerm` の追加 |
| `frontend/src/stores/app.ts` | `MondoTerm` 型、`SyndromeEntry` の4フィールド |
| `frontend/src/components/MondoTermList.vue` | 新規。セル内に MONDO 用語を縦積みする |
| `frontend/src/components/Results.vue` | 症候群テーブルに3列追加、遺伝子由来チップ |
| `frontend/src/components/Export.vue` | TSV / Excel 向けに配列フィールドを平坦化 |
| `frontend/src/locales/*.json` | 全10ロケールに `resultsPage.mondo` を追加 |
| `README.md` / `README-be.md` | データ配置とレスポンス仕様 |

列ヘッダは既存が英語ハードコードなので、新しい3列も英語固定とした。i18n 化は別件とする。

## 動作確認

`docker compose build && docker compose up -d` の後、`cdls_demo.png` で `/api/predict` を検証した。

起動ログ:

```
Load MONDO index: 58517 terms, 1609 syndrome keys
```

1,609 = MONDO 1,560 語 + GMDB フォールバック 49 グループ。

HPO 無し・HPO 有り（`HP:0000664`, `HP:0011304`, `HP:0001511`）の両方で確認した結果。

```
syndromes: 1603   genes: 1397   patients: 100
with mondo_id: 1554   fallback: 49
mondo_source: omim 1002, gene 552, null 49
PP4 support: すべて "Not available yet"
pcf matched: 0 (HPO 無し) / 1396 (HPO 有り)
1枚で複数症候群を支持する画像: 121
```

CdLS のデモ画像で上位が CdLS 1型 → CdLS（上位概念）→ 2型 → 3型 と並び、親に
`MONDO:0016033 Cornelia de Lange syndrome`、祖父母に `MONDO:0002254 syndromic disease` などが
出ることを確認した。HPO を与えると `MONDO:0957921 Cornelia de Lange syndrome 6`（遺伝子由来、
gm_rank 11）が PubCaseFinder rank 3 と組み合わさって meta_rank 4 に上がる。

自動チェックとして、全行で親・祖父母が MONDO ID 昇順であること、祖父母集合が親集合と
交わらないこと、PP4 が全行 "Not available yet" であることを検証している。

## 既知の制約

- **`transformation_probabilities_07052025.csv` は GMDB 疾患名でキーされている。** そもそも
  `format_syndrome_json()` の確率計算は条件式の `and False` で以前から無効化されており、
  `probability` / `ci_lower` / `ci_upper` は常に `None` である。今回それを有効化しても
  MONDO ラベルとは照合できないので、PP4 を復活させるときはキーの持ち方から再設計が要る
- **MONDO には非ヒト疾患の用語が含まれる。** 遺伝子経由の解決で稀に
  `dwarfism, GON4L-related, cattle` のような用語が候補に出る。除外するならフェーズ1の
  マッピング側で対処するのが筋
- **患者タブは OMIM 表示のまま。** `numeric_omim_id` / `phenotypic_series_id` を使い続けている。
  `image_id` 経由で MONDO を引くことは可能なので、将来の拡張候補
