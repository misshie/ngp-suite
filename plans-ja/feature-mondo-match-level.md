# MONDO の疾患単位による一致度の判定（案）

作成日: 2026-10-14
状態: 設計中（未実装。3 の「関連疾患群」の条件、広すぎる疾患単位、疾患単位のない用語の扱いが未決定）
対象リポジトリ: `ngp-suite`
作業ブランチ: `feat/mondo-distance-api`（[feature-mondo-ic-similarity.md](feature-mondo-ic-similarity.md) の続き）

## 背景

診断候補（id1）が正しい診断（id2）に「おおむね正解」かどうかを判定したい。
Lin 類似度の閾値には定説がなく、固定閾値には次の弱点がある。

- 総称の広さで値が変わる。NS3 と NS6 の組（Lin 0.7306）と、KS1 と KS2 の組（Lin 0.8907）は、どちらも総称の 1 段下の病型どうしだが、値が違う。
- MONDO の版や、IC の範囲のルートで値が変わる。

そこで、MONDO に入っている OMIM と Orphanet のキュレーションを使い、構造で判定する。Lin は合否に使わず、連続値の副次指標として報告する。

## 疾患単位

次のどちらかを持つ用語を「疾患単位」とする。

- `xref: OMIMPS:…` で、source に `MONDO:equivalentTo` を含むもの（OMIM の Phenotypic Series）
- `subset: ordo_disorder`（Orphanet の disorder）

ただし、`subset: disease_grouping` か `subset: ordo_group_of_disorders` を持つ用語は除く。

- OMIMPS が付いていても、分類用の用語がある（例: craniosynostosis、ectodermal dysplasia syndrome、X-linked syndromic intellectual disability）。
- 同梱 OBO（2026-09-01）では、OMIMPS か `ordo_disorder` を持つ用語は 6,773 個、そのうち分類用の subset も持つものは 119 個。除いた後の疾患単位は、範囲内で 6,543 個。

例:

| 用語 | 付いている情報 | 疾患単位 |
|---|---|---|
| MONDO:0016512 Kabuki syndrome | OMIMPS:147920、`ordo_disorder`（Orphanet:2322） | はい |
| MONDO:0018997 Noonan syndrome | OMIMPS:163950、`ordo_disorder`（Orphanet:648） | はい |
| MONDO:0015280 cardiofaciocutaneous syndrome | OMIMPS:115150、`ordo_disorder`（Orphanet:1340） | はい |
| MONDO:0012371 Noonan syndrome 3 などの病型 | OMIM の xref のみ | いいえ |
| MONDO:0020297 Noonan syndrome and Noonan-related syndrome | `disease_grouping`、`ordo_group_of_disorders`（Orphanet:98733） | いいえ |
| MONDO:0019042 multiple congenital anomalies/dysmorphic syndrome | `disease_grouping`、`ordo_group_of_disorders` | いいえ |

各用語の「疾患単位」は、その用語自身を含む is_a の祖先のうち、最も近い疾患単位とする。
病型（NS3、KS1 など）は 1 段上の総称に引き上げられる。総称は自分自身が疾患単位になる。

## 判定（4 段階）

1. **完全一致**: id1 = id2
2. **同一疾患単位**: 両者の疾患単位が同じ
3. **関連疾患群**: 疾患単位どうしの MICA までの hops が、いずれも 1 以下（追加の条件が必要。後述）
4. **不正解**: それ以外

### 2 を細分しない理由（メンテナの判断）

2 には、包含の関係（Kabuki syndrome と KS1）と、隣の病型（KS1 と KS2）が両方入る。これを区別しない。

- ギャラリーには古い症例があり、総称までしか診断がついていないものもある。
- 診断しようとする症例に最も近いのが、そうした古い症例であることも想定している。
- そのため、総称と病型の包含を「疾患単位としての一致」と扱うのは、この方式の利点と考える。

### hops を疾患単位で数える理由

生の hops では、病型の段の分だけ hops が膨らむ。

| id1 | id2 | MICA | 生の hops | 疾患単位での hops | Lin |
|---|---|---|---|---|---|
| NS3 | CFC1（MONDO:0007265） | MONDO:0020297 | [2, 2] | [1, 1] | 0.6617 |
| Noonan syndrome | CFC1 | MONDO:0020297 | [1, 2] | [1, 1] | 0.7647 |
| Kabuki syndrome | Noonan syndrome | MONDO:0019042 | [2, 2] | [2, 2] | 0.4035 |

生の hops ≤ 2 で判定すると、NS3 と CFC1 は通るが、Kabuki と Noonan も通ってしまう。
疾患単位にそろえれば、前者は [1, 1]、後者は [2, 2] になり、hops ≤ 1 で切り分けられる。

MONDO:0020297 の下には、顔貌は似ているが原因の異なる疾患が並ぶ。Noonan syndrome、CFC syndrome、Costello syndrome、Legius syndrome、NSML、Noonan syndrome-like disorder with loose anagen hair の 6 つで、いずれも疾患単位である。
これらの組を「関連疾患群」として拾うのが、3 の狙いである。

## 未解決の課題

### 課題 1: hops ≤ 1 だけでは、3 が広すぎる

大きな分類用の用語の直下に疾患単位が並んでいると、無関係な疾患どうしでも [1, 1] になる。

| id1 | id2 | MICA | 疾患単位での hops | Lin |
|---|---|---|---|---|
| Kabuki syndrome | Williams syndrome | MONDO:0002254 syndromic disease | [1, 1] | 0.2038 |
| Kabuki syndrome | Neu-Laxova syndrome | MONDO:0015159 MCA/DS-intellectual disability | [1, 1] | 0.446 |
| Noonan syndrome | Legius syndrome | MONDO:0020297 | [1, 1] | 0.7647 |

ギャラリーでは、上限なしで 3 に当たる疾患単位の組が 21,114 組あった（後述の集計）。大半は syndromic disease（6,155 組）、MCA/DS-ID（4,661 組）、hereditary disease（4,533 組）が MICA になる組である。

MICA の大きさに上限を設ける案を、ギャラリーで試した。

- **直下の疾患単位の数で数える（最初の案 A）は不適。** 直下の疾患単位は少なくても、下位の分類を多く持つ広い用語がすり抜ける。例: musculoskeletal system disorder（直下の疾患単位 9）、chromosomal disorder（5）、neurodevelopmental disorder（7）。
- **子孫数で数えると、上の穴はふさがるが、閾値がもろい。**

| MICA の子孫数の上限 | 3 に当たる組 | MICA になる用語 |
|---|---|---|
| 20 | 75 | 55 |
| 30 | 154 | 71 |
| 50 | 568 | 94 |
| 100 | 727 | 114 |
| 200 | 1,303 | 131 |

  - MONDO:0020297 の子孫数は 29。上限 30 の内側にぎりぎり入る。その親の RASopathy（MONDO:0021060）は 37 で、上限 30 では外れる。
  - 上限 30 でも、表現型のまとまりとは言いにくい用語が残る。例: telecanthus、patent ductus arteriosus、hypertrichosis、subcutaneous tissue disorder、monogenic epilepsy、autosomal recessive syndromic intellectual disability（子孫数 7）。
  - 一方、表現型のまとまりとして妥当そうな用語も多い。例: mandibulofacial dysostosis、Marfan and Marfan-related disorder、otopalatodigital syndrome spectrum disorder、acrofacial dysostosis、FGFR3-related chondrodysplasia、BAFopathy、progeroid syndrome。

案は次のとおり。

- **案 B'（推奨）: 子孫数で候補を絞り、臨床医が許可リストを作る。**
  - 子孫数 50 以下でギャラリーの組の MICA になる用語（94 個）を候補にする。
  - 臨床医が「顔貌の類似した疾患群」として認めるものを選ぶ。
  - 許可リストを MONDO の版とあわせて固定し、論文に付録として載せる。
  - 用語ごとに判断の根拠を残せるので、固定閾値より説明しやすい。
- **案 A': 子孫数の上限 D だけで判定する。** 手作業はないが、上の例のように閾値がもろく、無関係な群も拾う。
- **案 C: 3 を設けない。** 判定は 1、2、4 の 3 段階にし、関連疾患群は Lin などで副次的に示す。

### 課題 2: 広すぎる疾患単位

分類用の subset を除いても、子孫の多い疾患単位が残る。ギャラリーの用語のうち、子孫数 50 以上の疾患単位に引き上げられるものがある。

| 疾患単位 | 子孫数 | 引き上げられるギャラリーの用語 |
|---|---|---|
| MONDO:0100172 intellectual disability, autosomal dominant | 95 | 22 |
| MONDO:0100062 genetic developmental and epileptic encephalopathy | 129 | 17 |
| MONDO:0019502 autosomal recessive non-syndromic intellectual disability | 71 | 15 |
| MONDO:0019181 non-syndromic X-linked intellectual disability | 52 | 9 |
| MONDO:0100038 complex neurodevelopmental disorder | 189 | 3 |

上の 4 行だけで 63 用語になる。いずれも原因遺伝子ごとの病型で、顔貌も違いうる。これらが互いに「同一疾患単位」になるのは不適切。

- 案: 子孫数が一定以上（例: 50 以上）の用語は、疾患単位とみなさない。その下の病型は引き上げず、自分自身で比べる（課題 3 の 1 と同じ扱い）。
- 子孫数 50 未満の疾患単位でギャラリーの用語を複数集めるものは、AR primary microcephaly（5 用語、子孫数 32）、congenital myasthenic syndrome（3、37）、holoprosencephaly（2、20）など。これらを同一疾患単位とするかも、あわせて確認する。

### 課題 3: 端の場合

ギャラリーの集計では、最も近い疾患単位の内訳は次のとおり。

| 区分 | 用語数 |
|---|---|
| 自分自身が疾患単位 | 446 |
| 1 段上に引き上げ | 228 |
| 2 段上に引き上げ | 24 |
| 3 段上に引き上げ | 2 |
| 最も近い疾患単位が複数 | 4 |
| 疾患単位の祖先がない | 195 |

1. **疾患単位の祖先がない用語（195 個、約 22%）**
   - 例: Basilicata-Akhtar syndrome、Dias-Logan syndrome、Chopra-Amiel-Gordon syndrome、chromosome 15q24 deletion syndrome。
   - OMIM の単一の項目で、Phenotypic Series にも Orphanet の disorder にも当たらない疾患が多い。
   - 前回の案（一律に 4）は不適。**その用語自身を疾患単位とみなす**よう改める。2 は完全一致のときだけになり、3 は課題 1 の方式で判定できる。
2. **最も近い疾患単位が複数ある用語（4 個）**
   - 例: Aarskog-Scott syndrome, X-linked（FG syndrome と faciodigitogenital syndrome）、developmental and epileptic encephalopathy の病型（infantile spasms と genetic DEE）。
   - 案: 候補をすべて持たせる。どれか 1 組でも一致すれば 2 とし、3 も組のうち最も近いもので判定する。
3. **疾患単位の子が疾患単位**（例: NSML の下の LEOPARD 1〜3）: 自分自身を含めて最も近い単位を使う。LEOPARD 2 は NSML に引き上げ、それより上には上がらない。

### ギャラリーの集計の条件

- 入力: GMDB v1.1.4 のメタデータ pickle の `disorder_metadata`（1,091 疾患）。患者ごとの情報は使っていない。
- OMIM ID を、Stage 2 と同じ関数（`map_GMDBomim_to_mondo.py` の `parse_obo` と `resolve_lookup_keys`）で MONDO に写した。写せたのは 899 疾患で、192 疾患は OMIM から写せなかった。
- 実際の MONDO 版 pickle は、遺伝子からの対応も使う。そのため、上の数は近似である。MONDO 版 pickle が `NGPSUITE_GMDB_DIR` に置かれたら数え直す。
- 画像数による重み付けはしていない。

## 次の作業

1. 課題 1〜3 の方式を決める。
   - 3 を案 B'（候補 94 個を臨床医が選別）、案 A'、案 C のどれにするか
   - 広すぎる疾患単位の上限（例: 子孫数 50）
   - 疾患単位の祖先がない用語を自分自身の単位とみなすこと
2. 案 B' の候補の一覧を臨床医向けに出力した（2026-10-14、メンテナが案 B' を選択）。
   - ギャラリー由来の情報を含むので、リポジトリの外に置く（TSV と、Excel 用の BOM 付き CSV）。
   - 現行の定義で 94 個、課題 2 と 3 の改訂案（子孫数 50 以上の単位を除き、単位のない用語は自分自身を単位とする）で 104 個。改訂案は現行の 94 個をすべて含み、10 個を加える。
   - 列: MONDO ID、英語名、日本語名、子孫数、Seco IC、直下の疾患単位の数、subset、Orphanet、両定義での候補の別・組の数・直下のギャラリーの疾患単位、判定欄、コメント欄。
   - 判定基準（メンテナが決定）: 「この群に属する疾患は、顔貌を含む臨床像が互いに似ていて、互いに鑑別診断に挙がるか」。
     - 顔貌の類似を中心に判断する。分子機序や臓器でまとまるだけの群（例: familial long QT syndrome）は承認しない。
     - 「個別の疾患の群であること」は必要条件だが、十分条件ではない。
     - 群の一部だけが似ている場合は reject とし、似ている組をコメントに残す（承認は群のすべての組に及ぶため）。
   - 判定欄は `related_group (approve/reject/hold)`。判定者向けの手引きを一覧と同じ場所に置いた。
   - 臨床医の判定を受けて、許可リストを確定する。
3. 実装する。
   - `load_mondo_index` で、OMIMPS の xref（equivalentTo）と `subset` を読む
   - `lib/mondo.py` に疾患単位の解決と判定の関数を加え、`/api/mondo/distance` の応答に判定を加える
   - 許可リストを使う場合は、MONDO の版とあわせて `backend/mondo/` に置く
   - API は対称な判定だけを返す。id1 を候補、id2 を正解とする解釈は呼び出し側に任せる
4. 単体テスト、README と README-ja の「6. MONDO の距離と類似度の API」の節、引き継ぎメモを更新する。

## 検証に使った値

同梱 OBO（2026-09-01）、Seco の IC、範囲のルート MONDO:0700096。

| id1 | id2 | MICA | 生の hops | Lin | 判定（案） |
|---|---|---|---|---|---|
| KS1 | Kabuki syndrome | MONDO:0016512 | [1, 0] | 0.9422 | 2 |
| KS1 | KS2 | MONDO:0016512 | [1, 1] | 0.8907 | 2 |
| NS3 | NS6 | MONDO:0018997 | [1, 1] | 0.7306 | 2 |
| NS3 | Noonan syndrome | MONDO:0018997 | [1, 0] | 0.8444 | 2 |
| Noonan syndrome | CFC syndrome | MONDO:0020297 | [1, 1] | 0.8426 | 3 |
| Noonan syndrome | Costello syndrome | MONDO:0020297 | [1, 1] | 0.7647 | 3 |
| Noonan syndrome | NSML | MONDO:0020297 | [1, 1] | 0.8309 | 3 |
| NS3 | CFC1 | MONDO:0020297 | [2, 2] | 0.6617 | 3 |
| NS3 | LEOPARD 2 | MONDO:0020297 | [2, 2] | 0.6617 | 3 |
| Kabuki syndrome | Noonan syndrome | MONDO:0019042 | [2, 2] | 0.4035 | 4 |
| Kabuki syndrome | Williams syndrome | MONDO:0002254 | [1, 1] | 0.2038 | 4（課題 1 の制限が必要） |
| Kabuki syndrome | Neu-Laxova syndrome | MONDO:0015159 | [1, 1] | 0.446 | 4（課題 1 の制限が必要） |
| Williams syndrome | Down syndrome | MONDO:0020049 | [4, 2] | 0.4460 | 4 |
