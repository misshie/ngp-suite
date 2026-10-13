# MONDO 距離 API への情報量（IC）類似度の追加

作成日: 2026-10-13
状態: 実装済み・検証済み（2026-10-13、単体テストと Docker 上のエンドポイント）
対象リポジトリ: `ngp-suite`
作業ブランチ: `feat/mondo-distance-api`（[feature-mondo-distance.md](feature-mondo-distance.md) の続き）

## 背景

`GET /api/mondo/distance` は is_a の経路長（ホップ数）しか返さない。
ホップ数は、階層の深さや枝の密度に左右される。そこで、intrinsic IC に基づく Resnik と Lin の類似度を同じ応答に加える。
既存のフィールドと挙動（422 と 404、範囲外の ID でも距離を返すこと）は変えない。

## 定義

- 範囲: is_a エッジのみを使う。ルート（既定は `MONDO:0700096` human disease）の子孫に限り、ルート自身を含める。
  - obsolete は `load_mondo_index` が除外済み。多重継承はそのまま扱う。
  - 範囲外の親へのエッジは数えない。
- `N` = 範囲内の用語数（同梱 OBO 2026-09-01 で 23,238）
- `desc(c)` = 範囲内での子孫数（自身を含まない）。子孫集合を int のビットセットで和集合にするので、多重継承でも重複して数えない。
- IC
  - `descendants`（既定）: `-ln((desc+1)/N)`。ルートで 0、葉で `ln N`。
  - `seco`: `1 - ln(desc+1)/ln N`。`descendants` の IC を `ln N` で割ったものと同じなので、Lin は 2 つの方法で一致し、Resnik だけが [0, 1] に縮む。
- 共通祖先: 用語自身を含むそれぞれの祖先集合の積集合を、範囲内に限ったもの。
- MICA: IC が最大の共通祖先。同値は `mica_ties` に ID 順で全て並べ、`mica` はその先頭にする。
  - IC は祖先に向かって厳密に減る。このため MICA は必ず最も近い共通祖先（`common_ancestors`）の 1 つになる。
- Resnik = IC(MICA)
- Lin = 2·IC(MICA)/(IC(a)+IC(b))
  - 同一用語なら 1。異なる用語で分母が 0 なら `null`。
  - 分母が 0 になるのは a = b = ルートのときだけなので、実際には後者は起こらない。
- a か b が範囲外なら、`mica`、`resnik`、`lin` は `null`、`mica_ties` は `[]`。

## キャッシュ

子孫数の計算は約 0.35 秒（OBO の読み込みは約 2.5 秒）。ファイルには書かず、メモリにだけ持つ（メンテナの決定）。
- 起動時に既定のルートで計算する。
- 別のルートを指定されたら、初回だけ計算する。
- `main.py` の `_mondo_ic` に、最近使った順で最大 8 件のルートを保持する。

OBO はイメージに焼き込まれ、プロセスで 1 つしか読まないので、これで「MONDO の版ごとに 1 回」と同じ効果になる。

## API

既存の `GET /api/mondo/distance` に任意のクエリを足す。
- `ic_method`: `descendants` | `seco`。それ以外は 422。
- `ic_root`: MONDO ID の形式でなければ 422、OBO になければ 404。

応答に加わるもの:

- `common_ancestors[*].ic`
- `mica`: `{id, name, labels, ic}`
- `mica_ties`: `mica` と同じ形の配列
- `resnik`、`lin`
- `ic_params`: `{method, scope_root, n_terms, mondo_version}`

## 検証用の値

同梱の OBO（2026-09-01）で、`descendants` 法、ルート `MONDO:0700096` で確認した値。

| A | B | IC(A) | IC(B) | MICA | Resnik | Lin |
| --- | --- | --- | --- | --- | --- | --- |
| MONDO:0016512 Kabuki syndrome | MONDO:0007843 Kabuki syndrome 1 | 8.9549 | 10.0535 | MONDO:0016512 | 8.9549 | 0.9422 |
| MONDO:0007843 Kabuki syndrome 1 | MONDO:0008678 Williams syndrome | 10.0535 | 10.0535 | MONDO:0002254 syndromic disease | 1.9374 | 0.1927 |

2 行目の候補だった `disease of genetic or genomic mechanism`（MONDO:7770009）の IC は 0.6399 で、`syndromic disease`（1.9374）より低い。
`seco` では、Lin は同じ値で、Resnik は 0.8907 と 0.1927 になる。

テストは `backend/tests/test_mondo_ic.py`（標準ライブラリの unittest）。`cd backend && python3 -m unittest discover -s tests -v` で実行する。
