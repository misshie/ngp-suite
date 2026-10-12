# GMDB-MONDO: GMDB画像メタデータへのMONDO疾患用語の付与

*English version: [README.md](README.md)*

## このディレクトリについて

このディレクトリでは、GMDB のメタデータから NGPsuite のギャラリー用メタデータ pickle（`patient_metadata_*_mondo.p`）を作るスクリプトを公開しています。想定ユーザーは、実質的には GMDB のメタデータにアクセスできる GMDB 運営者です。NGPsuite の利用者がこのスクリプトを実行する必要はありません。完成した pickle は、ほかの GMDB ファイルと一緒に提供されます。

スクリプトの正本は別の非公開リポジトリで管理しており、ここにはそのスナップショットを置いています。パイプラインを変更したときに、手動で更新します。

**データは同梱していません。** GMDB のメタデータと、そこから派生したファイルは個人情報を含みうるため、GMDB の利用条件に従って入手してください。このディレクトリの `.gitignore` は、`*.p`、`*.tsv`、`*.csv`、`*.err.txt` とオントロジーのファイルを除外し、誤ってコミットされないようにしています。

### 実行手順の概要

Stage 1 はカレントディレクトリを Docker コンテナにマウントします。そのため、スクリプトとデータを 1 つの作業ディレクトリに置き、すべての Stage をそこで実行してください。作業ディレクトリはリポジトリの外に置きます。

```sh
mkdir -p ~/gmdb-mondo-work
cp tools/gmdb-mondo/*.sh tools/gmdb-mondo/*.py tools/gmdb-mondo/*.ru ~/gmdb-mondo-work/
cp backend/mondo/mondo-international.obo.gz ~/gmdb-mondo-work/   # Stage 1 を実行する場合は不要
cp /path/to/patient_metadata_2026-05-23.tsv ~/gmdb-mondo-work/    # GMDB のエクスポート
cd ~/gmdb-mondo-work
python3 020_map_GMDBomim_to_mondo.py 2> patient_metadata_2026-05-23_mondo.err.txt
python3 030_build_metadata_pickle.py --validate
cp patient_metadata_2026-05-23_mondo.p "$NGPSUITE_GMDB_DIR/data/"
```

`$NGPSUITE_GMDB_DIR` は、NGPsuite が起動時にマウントする GMDB データのディレクトリです（[`backend/.env.example`](../../backend/.env.example) と、トップの [README-ja](../../README-ja.md) を参照）。pickle を差し替えたら、`backend/` で `docker compose restart api` を実行します。

Stage 1 が必要なのは、MONDO を更新するときだけです。それ以外は NGPsuite に同梱の OBO（`backend/mondo/mondo-international.obo.gz`）を使ってください。pickle と実行時のオントロジーが、同じ MONDO リリースにそろいます。

## 概要

このパイプラインは、GestaltMatcher Database (GMDB) の画像メタデータに [MONDO](https://mondo.monarchinitiative.org/) の疾患用語を付与します。GMDBの各レコードはOMIM IDおよび／または遺伝子シンボルを持っており、パイプラインはこれらをMONDO用語に解決し、さらにその親クラス・祖父母クラスを付加します。これにより、レコードを疾患階層のより粗い粒度でグルーピングできます。

パイプラインは3段階です。

1. MONDO international editionをOWLからOBO形式へ変換する（`010_run-docker-robot-owl2obo.sh` と `preprocess_labels_for_obo.ru`）。
2. メタデータTSV中のOMIM IDと遺伝子シンボルをMONDO用語にマッピングする（`020_map_GMDBomim_to_mondo.py`。本体は `map_GMDBomim_to_mondo.py`）。
3. `mondo_id` を含む NGPsuite 互換メタデータ pickle を生成する（`030_build_metadata_pickle.py`）。

Stage 2・3 は Stage 1 が生成する `mondo-international.obo.gz` を読みます。

オントロジー成果物はgzip（`.owl.gz` / `.obo.gz`）で受け渡します。ROBOTはgzip入力を安定して読めないため、シェルラッパが作業ディレクトリ内の一時ファイルへ展開し、ROBOTにはgzip付きOBOの直接出力を依頼します。

**番号付き Python エントリについて:** Python は先頭が数字のモジュール名を `import` できません。`020_…` は `map_GMDBomim_to_mondo.main` を呼ぶ薄いラッパーです。本体ファイルは改名しないでください（`010` = Stage 1、`020` = Stage 2、`030` = Stage 3）。

## データソース

### MONDO international edition

`mondo-international.owl` / `mondo-international.owl.gz` は、MONDOのダウンロードページ <https://mondo.monarchinitiative.org/pages/download/> より、PURL <https://purl.obolibrary.org/obo/mondo/mondo-international.owl> を経由して取得しました（取得日: **2026-09-18**、MONDO リリース **2026-09-01**）。

international editionはmain OWL editionと同等の内容に加えて、コミュニティによってキュレーションされた各言語の翻訳を含みます（日本語翻訳はライフサイエンス統合データベースセンター (DBCLS) の藤原豊史氏・高月照江氏が主導）。MONDOはCC BY 4.0で配布されています。

OWL はここには同梱していません（gzip で約15 MB、非圧縮で約271 MB）。Stage 1 を実行する場合は、上記の PURL から取得し、`mondo-international.owl.gz` として gzip 圧縮してください。

### GMDB画像メタデータ

`patient_metadata_2026-05-23.tsv` は、現行の NGPsuite ギャラリーに使った GMDB 患者／画像メタデータ（28,499レコード）です。同梱していません。GMDB 運営者が GMDB から入手します。Stage 2（マッピング）の出力は `patient_metadata_2026-05-23_mondo.tsv` です。

## 実行環境

- Docker（Stage 1で `obolibrary/robot` イメージを取得・実行します）
- コンテナ内のJVMが利用できるメモリ約16 GB以上（Stage 1は `-Xmx16G` を指定）
- Python 3.9以降（標準ライブラリのみ使用）
- `gzip` / `gunzip`（シェルラッパが使用）

## ファイル構成

| ファイル | 役割 |
| --- | --- |
| `010_run-docker-robot-owl2obo.sh` | Stage 1実行スクリプト: 必要なら入力を展開、ROBOT `query`、`.obo.gz` を出力 |
| `preprocess_labels_for_obo.ru` | Stage 1のラベル正規化用SPARQL Updateルール |
| `020_map_GMDBomim_to_mondo.py` | Stage 2の薄いラッパー（`from map_GMDBomim_to_mondo import main`） |
| `map_GMDBomim_to_mondo.py` | Stage 2のマッピング本体（`.obo` / `.obo.gz` 対応・import 可能） |
| `mondo_gene_resolution.py` | Stage 3: 空 `gene_names` 行の MONDO 分類ヘルパ |
| `030_build_metadata_pickle.py` | Stage 3: TSV → NGPsuite用メタデータ pickle |
| `mondo-international.owl.gz` | Stage 1の入力（約15 MB。非圧縮 `.owl` と両方ある場合はこちらを優先）。*同梱なし・要取得* |
| `mondo-international.obo.gz` | Stage 1の出力／**Stage 2・3で使うオントロジー**（58,942用語、約8.1 MB）。*NGPsuite に `backend/mondo/mondo-international.obo.gz` として同梱* |
| `patient_metadata_2026-05-23.tsv` | Stage 2の入力。*同梱なし・GMDB のエクスポート* |
| `patient_metadata_2026-05-23_mondo.tsv` | Stage 2の出力／Stage 3の入力 |
| `patient_metadata_2026-05-23_mondo.err.txt` | Stage 2の標準エラー出力ログ |
| `patient_metadata_2026-05-23_mondo.p` | Stage 3の出力（NGPsuite互換pickle） |

GMDBメタデータとそこから派生したファイル（`*.p`、`*.tsv`、`*.csv`、`*.err.txt`）は個人情報を含みうるため、決してコミットしないでください。共有は GMDB の利用条件の範囲内に限ります。

## Stage 1: ラベル正規化を伴うOWL→OBO変換

```sh
./010_run-docker-robot-owl2obo.sh
```

`mondo-international.owl.gz` があればそれを、なければ `mondo-international.owl` を選びます。gzip入力の場合は一時ファイル `.tmp-mondo-international.owl.*` に展開し（終了時に削除。Docker 内の ROBOT が読めるよう展開後に `chmod a+r`）、`obolibrary/robot` コンテナ内で `robot query --update preprocess_labels_for_obo.ru --format obo --output mondo-international.obo.gz` を実行します（`JAVA_TOOL_OPTIONS="-Xmx16G -Dfile.encoding=UTF-8"`）。

SPARQL Updateが必要な理由は、OBO形式が1用語につき `name` を1つしか許さない一方で、international editionは言語ごとに `rdfs:label` を持つためです。正規化を行わないとOBO出力が失敗するか、意図しないラベルが出力されます。ルールは次の順に適用されます。

1. **英語以外のラベルを代替ラベルへ移す。** 言語タグが `en` でも空でもない `rdfs:label` をすべて削除し、言語タグを文字列自体に埋め込んだ `skos:altLabel` として再挿入します（例: MONDO:0000005の日本語ラベルは `"脱毛症, 孤立性@ja"` となります）。削除されるラベルをreifyしているOWLアノテーション公理（`owl:annotatedSource`／`Property`／`Target`）も併せて削除します。変換後のOBOでは `property_value: altLabel "…@ja" xsd:string` として現れます。

2. **廃止用語の冗長なラベルを削除する。** `owl:deprecated true` を持つ用語が `"obsolete …"` で始まるラベルと元のラベルの両方を持つ場合、`"obsolete "` 始まりのラベルを残して他を削除します（こちらもreify公理を併せて削除）。

3. **複数ラベルが残る用語を1ラベルに縮約する。** なお複数の `rdfs:label` を持つ主語については、辞書順で最小のラベル文字列を残し、それ以外を `oboInOwl:hasExactSynonym` に変換します。これにより、ラベル文字列を失うことなく、OBO出力が要求する「1ノード＝1ラベル」の制約を満たします。

日本語ラベルは変換後も保持されます。OBOには `@ja` を含む文字列が26,560件含まれています。生成される `mondo-international.obo.gz` は、Stage 2 で廃止用語をスキップしたあと **58,942** 用語です。

## Stage 2: OMIM IDと遺伝子シンボルのMONDO用語へのマッピング

```sh
python3 020_map_GMDBomim_to_mondo.py \
  --input patient_metadata_2026-05-23.tsv \
  --obo mondo-international.obo.gz \
  --output patient_metadata_2026-05-23_mondo.tsv \
  2> patient_metadata_2026-05-23_mondo.err.txt
```

（`python3 map_GMDBomim_to_mondo.py …` でも同等です。）3つのオプションはいずれも上記の値がデフォルトなので、引数なしでも実行できます。`--obo` は `.obo` でも `.obo.gz` でも構いません。入力TSVには `omim_ids`、`gene_names`、`image_id`、`patient_id` の各列が必要です。

### オントロジー索引の構築

OBOファイルはスタンザ単位でパースされます。各 `[Term]` から `id`、`name`、`is_a`（親）、`xref`、`synonym`、遺伝子 `relationship` を記録し、`is_a` と `xref` の値からは末尾のOBOコメント（`! …`）と公理アノテーション（`{…}`）を除去します。

`is_obsolete: true` の用語は完全にスキップします。廃止用語も旧来のOMIM xrefを保持しており、xrefは最初に出現したスタンザが優先されるため、放置すると廃止用語が後継の現行用語を覆い隠してしまうためです。残る **58,942** 用語から3種類の索引を構築します。

- **OMIM索引**: `OMIM:` または `OMIMPS:` で始まるxrefをMONDO用語へ対応付けます。
- **遺伝子索引**: 大文字化した遺伝子シンボル。1つの遺伝子が複数のMONDO用語に対応することもあります。抽出元は2種類です。
  - MONDOがキュレーションした関連付け `relationship: has_material_basis_in_germline_mutation_in <HGNC IRI> {source="…"} ! <GENE>`。末尾のOBOコメントからシンボルを読み取ります。これが正式な情報源であり、索引の大半を占めます（現行OBO: 原因遺伝子用語 6,197／HGNCシンボル 4,645）。
  - 従来から使っているシノニム文字列のヒューリスティック3種。末尾が `"… caused by mutation in <GENE>"`、先頭が `"<GENE>-related …"`、`disease_series_by_gene` タグ付きシノニムの先頭の全大文字トークン。
  - ヒト以外の動物疾患（`MONDO:0005583` とその `is_a` 子孫 8,318 用語）は、遺伝子索引と原因遺伝子表から除外します（残る原因遺伝子用語は 6,197）。MONDO はこれらの用語にも相同なヒト遺伝子を付けているため、除外しないと例えば `KDM2B` の患者に *lethal multi-organ developmental dysplasia, KDM2B-related, cattle* まで付いてしまいます。用語名と `is_a` は残します。
- **階層索引**: 用語名と `is_a` の親。親・祖父母クラスの導出に使用します。

### レコード単位のマッピングルール

`omim_ids` セルはカンマとセミコロンで分割され、各トークンは通常のOMIM番号（`^\d+$`）、OMIM phenotypic series（`^PS\d+$`、大小文字非依存）、それ以外に分類されます。解決できる識別子はすべて採用するため、`mondo_id` は複数のIDを持つことがあります。

| `omim_ids` の内容 | 動作 | `mondo_source` | 理由コード |
| --- | --- | --- | --- |
| 通常のOMIM番号が1つ以上 | **すべて** `OMIM:<n>` で検索 | `omim` | `mapped_omim` |
| PS番号のみ | すべて `OMIMPS:<n>` で検索 | `omim` | `mapped_omimps` |
| 解決できるものが無い | `gene_names` にフォールバック | `gene` | `mapped_gene` |

PSを同格ではなく劣後させているのは意図的です。GMDBは疾患とその系列を併記することが多く（`239300, PS135900, PS239300`）、同格に扱うと疾患とその上位概念が2つの独立した症候群として出力されてしまいます。系列はMONDO階層の親として現れるので、情報は失われません。

遺伝子フォールバックは、OMIMから1件も用語が得られなかった場合に必ず実行されます。OMIM IDは存在するがオントロジーに無かった場合も含みます。セル内のすべての遺伝子シンボルを大小文字非依存で検索し、いずれかに登録されたMONDO用語をすべて採用します。

どちらの経路でも解決できなかったレコードは未マップとし、利用可能だった情報に応じて `unmapped_omim` / `unmapped_gene` / `unmapped_omim_gene` / `unmapped_no_identifier` に分類します。

### 出力

出力TSVは入力の全列をそのまま再現し、次の7列を追加します。

| 列 | 内容 |
| --- | --- |
| `mondo_id` | 一致したMONDO用語のID |
| `mondo_disease` | 一致した用語の名称 |
| `mondo_parent_id` | 一致した用語の `is_a` 親 |
| `mondo_parent_disease` | その親の名称 |
| `mondo_grandparent_id` | 親の `is_a` 親 |
| `mondo_grandparent_disease` | その祖父母の名称 |
| `mondo_source` | `omim` / `gene`。どちらの経路で解決したか |

親・祖父母は一致したすべての用語について収集し、見つかった順序を保ったまま重複を除去します。値が複数ある場合は `", "` で連結します。未マップのレコードは7列すべてが空になります。

`mondo_source` を設けたのは、2つの経路で確信度が異なるためです。遺伝子由来のレコードはその遺伝子が起こしうる疾患をすべて列挙するため、臨床的に不均一な集合になりがちです。`PDGFRB` は乳児筋線維腫症・特発性基底核石灰化症4・過成長症候群を同時に返します。下流の利用側がOMIM由来と区別できる必要があります。

未マップのレコードはすべて標準エラー出力に `unmapped<TAB><image_id><TAB><patient_id>` の形式で報告され、最後にサマリが出力されます。現行の実行結果のサマリは次のとおりです。

```
rows: 28499
mapped: 26812
failed: 1687
breakdown:
  mapped_gene: 3142
  mapped_omim: 21810
  mapped_omimps: 1860
  multi_mondo: 1089
  unmapped_gene: 380
  unmapped_no_identifier: 1301
  unmapped_omim: 6
```

すなわち、28,499レコードのうち26,812件（94.1%）にMONDOアノテーションが付与されました。キュレーション済み遺伝子 `relationship` を索引に取り込む前は84.5%でした。`multi_mondo` は複数IDが付いたマップ済みレコードの数で、`mapped_*` の内数です。未マップの最大集団 `unmapped_no_identifier` は、OMIM IDも遺伝子シンボルも持たないレコードです。

## Stage 3: NGPsuite用メタデータ pickle の生成

```sh
python3 030_build_metadata_pickle.py \
  --input patient_metadata_2026-05-23_mondo.tsv \
  --obo mondo-international.obo.gz \
  --validate \
  --report gene-resolution-report.csv \
  --compare image_gene_and_syndrome_metadata_pp4_23052026_v1.1.4.p
```

既定では `patient_metadata_2026-05-23_mondo.p` を書き出します。pickleは **TSVのみから** 構築します。`--compare` は任意で、GMDB 運営者だけが持つ従来の GestaltMatcher の pickle を構造の参考として読みます（データ源には使いません）。Stage 3 も Stage 2 と同じ `mondo-international.obo.gz` を読みます。`--no-gene-resolution` を指定すると従来の挙動に戻ります。従来の挙動では、`gene_names` が空の画像は疾患名を遺伝子シンボルの代わりに使います（*疾患名の代用エントリ*。生物学の偽遺伝子とは無関係です）。

### 選別規則

1. `image_type == 'Frontal face'` のみ残す（`--image-type all` で無効化可）。
2. 遺伝子名・疾患名・`mondo_id` のいずれも無い行は除外する（診断情報が未整備）。
3. 現行実行: 28,499行 → frontal 18,534行 → **採用 17,566枚**（除外 968枚）。

### 空の `gene_names` の MONDO 解決

`gene_names` が空の画像は、OBO の `has_material_basis_in_germline_mutation_in` だけを根拠に分類します（判定順固定）。

1. **`gene_unresolved`（染色体疾患）** — `MONDO:0019040` / `MONDO:0700064` の子孫で自身に原因遺伝子がない。Prader-Willi のように子に単一遺伝子疾患があっても、先に染色体側へ落とす。
2. **`mondo` 補完** — 自身の原因遺伝子がちょうど 1 つ → その遺伝子の `gene_internal_id` に合流（例: Kabuki syndrome 1 → KMT2D）。
3. **`subtype_expanded`** — 自身に遺伝子がなく子孫に候補がある（または自身に複数）→ **候補ごとに `gene_level` エントリを分割**する（例: Kabuki syndrome → KMT2D 行と KDM6A 行）。距離は実行時に同一 GM distance が付く。上流 v1.1.4 が OMIM Phenotypic Series で行っていた展開の MONDO 版。
4. **`gene_unresolved`（その他）** — 上記以外。

実測（17,566 枚中の空 gene 行 2,867 枚）: `mondo` 1,171 / `subtype_expanded` 610 / `gene_unresolved` 1,086。`--report` で GMDB フィードバック用 CSV を出力できます。

### 出力構造

NGPsuite（`backend/main.py`）互換の4つのトップレベル辞書です。

| ブロック | キー | 内容 |
| --- | --- | --- |
| `gene_level_metadata` | `image_id` → 非空リスト | 遺伝子（または疾患名の代用エントリ）単位の行 + `gene_source`（`gmdb` / `mondo`）。subtype 展開時は候補ごとに複数行 |
| `disorder_level_metadata` | `image_id` → 辞書 | 画像あたり1件の症候群中心レコード + `mondo_id: list[str]` |
| `gene_metadata` | `gene_internal_id` → 辞書 | `gene_name`, `gene_entrez_id`, `hgnc_id`, `gene_status` |
| `disorder_metadata` | `disorder_internal_id` → 辞書 | `disorder_name`, `omim_id`, `mondo_id: list[str]`, `mondo_source` |

`gene_status` は `gmdb` | `mondo` | `gene_unresolved`。

設計上の選択:

- **格納するMONDO列は `mondo_id` と `mondo_source` のみ**（親・祖父母・疾患名は載せない）。名称と階層は実行時に `mondo-international.obo.gz` から解決するため、オントロジーが更新されてもpickleが陳腐化しません。
- **`mondo_id` は `list[str]`**。未マップは空リスト。
- **PP4キーは持たせない**（`very_strong` / `strong` / `moderate` / `supporting`）。NGPsuiteの `get_pp4()` はキー欠落を「Not available yet」として扱い、`None` を入れると `TypeError` になります。
- **`internal_syndrome_*` は使わない**。疾患同一性は `mondo_id`（優先）→ `disorder_names` → `gene_names` の順で採番します。手動のsubtype→supertype付けは、利用時のMONDO階層探索に置き換えます。
- **`disorder_internal_id` / `gene_internal_id` は素の `int`**（`numpy.int64` ではない）。
- **単一遺伝子の MONDO 補完と subtype 展開は既存 ID へ合流**する。表示名だけ差し替えると NGPsuite の遺伝子重複排除で同じシンボルが二重になるため。

`--validate` はNGPsuiteの不変条件（非空のgeneリスト、internal IDの参照整合・画像内重複なし、`mondo_id` がlistであること、`mondo_source` が `mondo_id` と整合すること、PP4キー不在、`gene_status` / `gene_source` の整合）を検査します。

### 今回の実行結果（2026-10-06 再生成・非ヒト用語除外後）

```
adopted: 17566
with_mondo: 17303 without_mondo: 263
mondo_source omim: 15330 gene: 1973
images with >1 mondo_id: 707
genes: 1398
disorders: 1439
gene_resolution: {'gene_unresolved': 1086, 'mondo': 1171, 'subtype_expanded': 610}
```

採用画像の **98.5%** が1件以上のMONDO IDを持ちます（17,303 / 17,566）。遺伝子メタデータは subtype 展開後 1,398 件です（GMDB に無かった候補遺伝子を追加）。

残る263枚は、MONDOに疾患エントリ自体が存在しない遺伝子（`PSMC3`、`SPATA5`、`KCTD3` など）です。`mondo_id` は空リストのままで、代わりに遺伝子シンボルでグルーピングされます。使用中のMONDO IDはすべてオントロジーに存在し、廃止用語ではなく、親を1件以上持ちます。

## ライセンスと帰属

スクリプトは NGPsuite の一部であり、そのライセンス（[LICENSE.md](../../LICENSE.md)、CC BY-NC 4.0）に従います。MONDOは [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) で配布されており、そこから派生したOBOファイルも同ライセンスを継承します。GMDBメタデータとそこから作った pickle は、GMDBのデータ利用条件に従います。
