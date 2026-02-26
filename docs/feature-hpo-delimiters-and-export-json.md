# HPO 区切り・Export JSON 機能の作業メモ

## 1. HPO 区切りの変更（本メモ）

### 目的
Upload Analysis File ダイアログの「Input comma-separated HPO IDs」で、**コンマに加えてセミコロン・タブ・スペース**を区切りとして許容する。

### 現状
- **frontend/src/components/Analysis.vue**
  - テキストエリアの値 `hpoIds` を送信時に `.split(',')` で分割している（107–111 行付近）。
  - ラベルは英語でハードコード: `"Input comma-separated HPO IDs"`（179 行付近）。

### 変更案

#### A. フロントエンド（Analysis.vue）

1. **パース処理の変更**
   - 現在: `hpoIds.value.split(',').map(id => id.trim()).filter(Boolean)`
   - 変更後: 区切りを「コンマ・セミコロン・タブ・スペース（改行含む）」のいずれか 1 文字以上にし、trim と空文字除去はそのまま。
   - 例（正規表現）:  
     `hpoIds.value.split(/[,;\s]+/).map(id => id.trim()).filter(Boolean)`  
     `\s` でスペース・タブ・改行をまとめて扱える。

2. **ラベルの多言語化**
   - 文言を「コンマ、セミコロン、タブ、スペースのいずれかで区切れる」旨に変更し、`analysisDialog.inputHpoIdsLabel` のようなキーで全ロケールに追加。
   - テンプレートでは `label="Input comma-separated HPO IDs"` を `:label="t('analysisDialog.inputHpoIdsLabel')"` に変更。

#### B. ロケール（全 10 言語）

- `analysisDialog` に `inputHpoIdsLabel` を追加。
- 例（en-US）:  
  `"inputHpoIdsLabel": "Input HPO IDs (comma, semicolon, tab, or space separated)"`
- 他言語も同様の意味で追加（日本語例: 「HPO ID を入力（カンマ・セミコロン・タブ・スペースのいずれかで区切り）」）。

#### C. バックエンド

- API は `hpo_ids: string[]` を受け取るだけなので**変更不要**。
- （任意）`backend/pingpong_client.py` の `args.hpo.split(',')` を同様に `re.split(r'[,;\s]+', args.hpo)` などにすると、CLI でも同じ区切りが使える。

### 変更ファイル一覧（HPO 区切り）

| ファイル | 内容 |
|----------|------|
| `frontend/src/components/Analysis.vue` | 区切りを `/[,\s;]+/`（または `/[,;\s]+/`）に変更、ラベルを `t('analysisDialog.inputHpoIdsLabel')` に変更 |
| `frontend/src/locales/en-US.json` | `analysisDialog.inputHpoIdsLabel` を追加 |
| `frontend/src/locales/ja.json` 他 8 言語 | 同上 |

### 動作確認のポイント

- コンマ区切り: `HP:0007655,HP:0045075` → 2 件として送信されること。
- セミコロン: `HP:0007655;HP:0045075` → 2 件。
- タブ: `HP:0007655\tHP:0045075` → 2 件。
- スペース・改行: `HP:0007655 HP:0045075` や複数行入力 → 2 件。
- 混在: `HP:0007655, HP:0045075; HP:0000175` → 3 件（前後の空白は trim で除去）。

---

## 2. Export JSON（別節で記載予定）

- Export Results で JSON 形式の出力を追加する。
- 詳細は後で追記。
