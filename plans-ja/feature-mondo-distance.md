# MONDO ID 間の距離を返す API

作成日: 2026-10-12
状態: 実装済み・ライブラリ関数は検証済み、エンドポイントは Docker での確認待ち
対象リポジトリ: `ngp-suite`
作業ブランチ: `feat/mondo-distance-api`（`main` から作成）

## 背景

2 つの MONDO ID が、MONDO の階層の上でどれだけ離れているかを知りたい。
MONDO の is_a は多重継承なので、2 つの用語を結ぶ経路は 1 本とは限らない。
そこで、全ての経路のエッジ数を配列で返し、あわせてその最小値も返す。今回はバックエンドだけを変更する。

## 距離の定義

- 辿るのは is_a エッジだけ。`relationship:`（`has_characteristic` など）は辿らない。
  `lib/mondo.py` の `load_mondo_index` が保持している `parents` をそのまま使う。
- 2 つの用語の「最も近い共通祖先」（LCA）を求める。
  - 共通祖先: 用語自身を含めたそれぞれの祖先集合の積集合。
  - LCA: 共通祖先のうち、他の共通祖先の祖先になっていないもの。複数あり得る。
- 各 LCA について、A から LCA への上向き経路と、B から LCA への上向き経路を全て組み合わせる。
  1 つの組のエッジ数の和を、1 経路の長さとする。
- 長さが同じでも、別の経路であれば別々に数える。
- LCA より上の共通祖先（根の `disease` など）を経由する経路は数えない。経路数が爆発するため。
- 一方が他方の祖先であれば、LCA はその祖先自身になり、上向きの経路だけを数えることになる。
- 同じ ID 同士は `[0]`。共通祖先がなければ `[]` で、`minimum` は `null`。

経路は列挙せず、経路長ごとの経路数（`Counter`）をメモ化再帰で数える。経路の多い組でもメモリを使い切らない。

## API

```
GET /api/mondo/distance?id1=MONDO:0008678&id2=MONDO:0008608
```

- `/api/predict` と同じ Basic 認証をかける。
- `id1` と `id2` は `^MONDO:\d{7}$` に一致しなければ 422 を返す。
- 同梱の OBO にない ID（廃止済みを含む）は 404 を返し、detail にその ID を書く。

応答の例:

```json
{
  "mondo_id_1": "MONDO:0008678",
  "mondo_id_2": "MONDO:0008608",
  "mondo_version": "2026-07-06",
  "distance": [6],
  "minimum": 6,
  "common_ancestors": [
    {"id": "MONDO:0020049", "name": "autosomal anomaly", "labels": {"en": "autosomal anomaly"}, "distance": [6]}
  ]
}
```

`common_ancestors` は LCA ごとの内訳で、各項目の `distance` を全て合わせると、上位の `distance` になる。

## 検証用の値

同梱の OBO（`backend/mondo/mondo-international.obo.gz`）で確認した値。

| A | B | distance | LCA |
| --- | --- | --- | --- |
| MONDO:0007336 isolated cleft palate | MONDO:0016064 cleft palate | [1] | MONDO:0016064 |
| MONDO:0008678 Williams syndrome | MONDO:0019040 chromosomal disorder | [4, 5] | MONDO:0019040 |
| MONDO:0008678 Williams syndrome | MONDO:0008608 Down syndrome | [6] | MONDO:0020049 |
| MONDO:0008678 Williams syndrome | MONDO:0007336 isolated cleft palate | [9, 10, 10, 11] | MONDO:7770006, MONDO:7770009 |
| MONDO:0007336 isolated cleft palate | MONDO:0000001 disease | [6, 7, 10] | MONDO:0000001 |
| MONDO:0007525 EDS, arthrochalasia type | MONDO:0000001 disease | [5, 6, 6] | MONDO:0000001 |

引数の順序を入れ替えても同じ結果になる。
