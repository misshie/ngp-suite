# MONDO 距離 API への情報量（IC）類似度と MICA までのホップ数の追加

作成日: 2026-10-13
状態: 実装済み・検証済み（2026-10-13。Seco の IC を既定にし、ホップ数を MICA までの組に置き換えた。単体テストと Docker 上のエンドポイントで確認）
対象リポジトリ: `ngp-suite`
作業ブランチ: `feat/mondo-distance-api`（[feature-mondo-distance.md](feature-mondo-distance.md) の続き）

## 背景

最初の版の `GET /api/mondo/distance` は、is_a の経路長しか返さなかった。最も近い共通祖先（LCA）を経由する全経路のエッジ数と、その最小値である。
ホップ数は、階層の深さや枝の密度に左右される。そこで、intrinsic IC に基づく Resnik と Lin の類似度を返すようにする。

ホップ数は、全共通祖先の中での最小値ではなく、MICA までの段数を (id1 側, id2 側) の組で返すように改めた。
- 組で返せば、どちらの側がどれだけ細かいか（方向と粒度の差）が読める。IC は対称な指標なので、この情報を持たない。
- 「共通の総称から 1 段下の病型どうし」のように、臨床の読者にも構造を説明しやすい。
- IC の結果がおかしいときに、MICA の位置と段数から原因を追える。

`distance` と `minimum` は廃止した（メンテナの判断。ブランチは未マージなので、外部への影響はない）。

## 定義

- 範囲: is_a エッジのみを使う。ルート（既定は `MONDO:0700096` human disease）の子孫に限り、ルート自身を含める。
  - obsolete は `load_mondo_index` が除外済み。多重継承はそのまま扱う。
  - 範囲外の親へのエッジは数えない。
- `N` = 範囲内の用語数（同梱 OBO 2026-09-01 で 23,238）
- `desc(c)` = 範囲内での子孫数（自身を含まない）。子孫集合を int のビットセットで和集合にするので、多重継承でも重複して数えない。
- IC
  - `seco`（既定）: `1 - ln(desc+1)/ln N`。ルートで 0、葉で 1。
  - `descendants`: `-ln((desc+1)/N)`。Seco の IC に `ln N` を掛けたものと同じなので、Lin は 2 つの方法で一致し、Resnik だけが縮尺を変える。
- 共通祖先: 用語自身を含むそれぞれの祖先集合の積集合。MICA を選ぶときは範囲内に限る。
- MICA: IC が最大の共通祖先。同値は `mica_ties` に ID 順で全て並べ、`mica` はその先頭にする。
  - IC は祖先に向かって厳密に減る。このため MICA は必ず LCA の 1 つになる。
- Resnik = IC(MICA)
- Lin = 2·IC(MICA)/(IC(a)+IC(b))
  - 同一用語なら 1。異なる用語で分母が 0 なら `null`。
  - 分母が 0 になるのは a = b = ルートのときだけなので、実際には後者は起こらない。
- ホップ数: `hops = [id1 側, id2 側]`。各用語からその祖先までの is_a のエッジ数で、経路が複数あれば最短を取る（幅優先探索）。
- a か b が範囲外なら、`mica`、`resnik`、`lin` は `null`、`mica_ties` は `[]`。`common_ancestors` はそのまま返す。

## キャッシュ

子孫数の計算は約 0.35 秒（OBO の読み込みは約 2.5 秒）。ファイルには書かず、メモリにだけ持つ（メンテナの決定）。
- 起動時に既定のルートで計算する。
- 別のルートを指定されたら、初回だけ計算する。
- `main.py` の `_mondo_ic` に、最近使った順で最大 8 件のルートを保持する。

## API

`GET /api/mondo/distance?id1=…&id2=…[&ic_method=seco|descendants][&ic_root=MONDO:…]`

- `ic_method` が不正な値なら 422 を返す。
- `ic_root` が MONDO ID の形式でなければ 422、OBO になければ 404 を返す。

応答の例（Kabuki syndrome 1 と Kabuki syndrome 2）:

```json
{
  "mondo_id_1": "MONDO:0007843",
  "mondo_id_2": "MONDO:0010465",
  "mondo_version": "2026-09-01",
  "common_ancestors": [
    {"id": "MONDO:0016512", "name": "Kabuki syndrome", "labels": {"en": "…", "ja": "…"}, "ic": 0.8907, "hops": [1, 1]}
  ],
  "mica": {"id": "MONDO:0016512", "name": "Kabuki syndrome", "labels": {"…": "…"}, "ic": 0.8907, "hops": [1, 1]},
  "mica_ties": ["（mica と同じ形の配列）"],
  "resnik": 0.8907,
  "lin": 0.8907,
  "ic_params": {"method": "seco", "scope_root": "MONDO:0700096", "n_terms": 23238, "mondo_version": "2026-09-01"}
}
```

## 検証用の値

同梱の OBO（2026-09-01）で、`seco` 法、ルート `MONDO:0700096` で確認した値。

| id1 | id2 | MICA | hops | Resnik | Lin |
| --- | --- | --- | --- | --- | --- |
| MONDO:0016512 Kabuki syndrome | MONDO:0007843 Kabuki syndrome 1 | MONDO:0016512 | [0, 1] | 0.8907 | 0.9422 |
| MONDO:0007843 Kabuki syndrome 1 | MONDO:0010465 Kabuki syndrome 2 | MONDO:0016512 | [1, 1] | 0.8907 | 0.8907 |
| MONDO:0007843 Kabuki syndrome 1 | MONDO:0008678 Williams syndrome | MONDO:0002254 syndromic disease | [2, 1] | 0.1927 | 0.1927 |
| MONDO:0008678 Williams syndrome | MONDO:0008608 Down syndrome | MONDO:0020049 autosomal anomaly | [4, 2] | 0.3928 | 0.4460 |
| MONDO:0012371 Noonan syndrome 3 | MONDO:0013186 Noonan syndrome 6 | MONDO:0018997 Noonan syndrome | [1, 1] | 0.7306 | 0.7306 |
| MONDO:0012371 Noonan syndrome 3 | MONDO:0018997 Noonan syndrome | MONDO:0018997 | [1, 0] | 0.7306 | 0.8444 |
| MONDO:0016512 Kabuki syndrome | MONDO:0018997 Noonan syndrome | MONDO:0019042 multiple congenital anomalies/dysmorphic syndrome | [2, 2] | 0.3271 | 0.4035 |

最後の行の LCA は 3 つある。`syndromic disease`（IC 0.1927、hops [1, 1]）、`hereditary disease`（MONDO:0003847、IC 0.0676、hops [1, 2]）、MONDO:0019042（IC 0.3271、hops [2, 2]）。
MICA は最短ホップの LCA とは限らない。ここでは 2 段上の MONDO:0019042 の方が、1 段上の `syndromic disease` より IC が高い。

3 行目のもう 1 つの LCA は `disease of genetic or genomic mechanism`（MONDO:7770009）。IC は 0.0636、hops は [3, 5] で、`syndromic disease` より IC が低い。
`descendants` 法では、Lin は同じ値になり、Resnik は `ln N` 倍になる（1 行目は 8.9549、3 行目は 1.9374）。

テストは `backend/tests/test_mondo_ic.py`（標準ライブラリの unittest）。`cd backend && python3 -m unittest discover -s tests -v` で実行する。
