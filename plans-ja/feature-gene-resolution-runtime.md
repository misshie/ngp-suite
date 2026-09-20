# GENES テーブルの遺伝子解決（実行時処理と表示）

作成日: 2026-09-18
更新: 2026-09-18（subtype 画像分割方式へ切り替え）
対象リポジトリ: `ngp-suite`
対になるプラン: `gmdb-mondo/plans-ja/2026-09-18-gene-resolution-builder.plan.md`

## 背景

GENES テーブルには、GMDB に原因遺伝子が登録されていない画像に由来する疑似遺伝子行が
含まれていた。静的な補完と subtype 展開は `gmdb-mondo` の pickle ビルダーが担う。

本プランは **実行時の表示と患者行の連結** を担当する。以前は `resolve_subtype_genes()` で
GM Distance 最小の候補へマージしていたが、上流 GestaltMatcher と同様に pickle 側で
候補ごとに `gene_level` エントリを分割する方式へ切り替えたため、実行時推論は不要になった。

## 前提となる pickle 契約

- `gene_metadata[gid]["gene_status"]`: `gmdb` | `mondo` | `gene_unresolved`
- `gene_metadata[gid]["hgnc_id"]`: `HGNC:7133` など。無ければ `None`
- `gene_level_metadata[image_id]`: 候補ごとに複数エントリ可。`gene_source` は `gmdb` | `mondo`

**後方互換**: 旧 pickle の `subtype_unresolved` / `subtype_candidates` は
`format_gene_json()` で疾患名行として表示するフォールバックのみ残す（新 pickle では発生しない）。

## 実装要点

1. `format_gene_json()` は `gene_status` を一次情報にし、`gmdb` / `mondo` / `gene_unresolved` を扱う。`hgnc_id` と `gene_source` を出力する。
2. `resolve_subtype_genes()` は削除済み。分割は `get_first_genes()` が同一 distance で展開する。
3. `format_subject_json()` は画像の全 `gene_level` エントリの `gene_name` / `gene_entrez_id` を `'; '` で連結する（PATIENTS の API / エクスポート用。UI テーブルには Gene Symbol 列はない）。
4. UI は「遺伝子未確定」と「MONDO 由来」チップを使用。「サブタイプ未確定」は旧 pickle 互換のため残置。

## 確認

- Kabuki / Joubert の疾患名行が GENES から消え、候補遺伝子行になる
- Williams syndrome は「遺伝子未確定」で残る
- Entrez 欠落の MONDO 補完遺伝子は HGNC リンクになる
