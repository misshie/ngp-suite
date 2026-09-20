# 初期画面「Get Started」パネルをクリックで Analysis を開く改良

## 目的
https://localhost/ の初期画面で表示される「Get Started / Press the Analysis button on the left navigation bar to start」パネルを、**直接クリックすると左ナビの Analysis ボタンと同じ動作**（Analysis ダイアログを開く）するようにする。

## 現状
- **default.vue**（レイアウト）: `isAnalysisOpen` を保持し、左ナビの Analysis ボタン `@click="isAnalysisOpen = true"` で `<Analysis v-model="isAnalysisOpen" />` を開いている。
- **Start.vue**: 初期画面の Get Started 用 `v-card` を表示。現状はクリック不可。

## 手順

### 1. レイアウトで `openAnalysis` を provide する（default.vue）

- `provide` を import し、`openAnalysis` というキーで「Analysis を開く」関数を提供する。
- その関数内で `isAnalysisOpen = true` を実行する。

```ts
// 例
import { ref, shallowRef, provide } from 'vue'

// setup 内
function openAnalysis() {
  isAnalysisOpen.value = true
}
provide('openAnalysis', openAnalysis)
```

### 2. Start.vue で `openAnalysis` を inject し、Get Started カードにクリックを付与

- `inject<() => void>('openAnalysis')` でレイアウトから関数を取得する。
- Get Started の `v-card` に以下を追加する：
  - `@click="openAnalysis?.()"` … クリックで Analysis を開く。
  - `role="button"` … 意味づけ。
  - `tabindex="0"` … キーボードフォーカス可能に。
  - `@keydown.enter.prevent="openAnalysis?.()"` および `@keydown.space.prevent="openAnalysis?.()"` … エンター・スペースで同動作。
- クリック可能であることが分かるよう、`cursor: pointer` とホバー時の視覚フィードバック（例: `variant` や `hover` 用クラス）を検討する。

### 3. ロケール文の扱い（任意）

- 「Press the Analysis button on the left navigation bar to start」はそのままでもよい。
- より自然にするなら、例: 「Click this panel or the **Analysis** button on the left to start」などに変更し、全言語の `startPage.pressAnalysis` を揃えて更新する。

### 4. 動作確認

- 開発モードで `npm run dev` を起動し、`/` で初期画面を表示。
- Get Started パネルをクリック → Analysis ダイアログが開くこと。
- 左ナビの Analysis ボタンを押す → 従来どおり開くこと。
- パネルにフォーカスして Enter / Space → 同様に開くこと。

---

## 変更対象ファイル（想定）

| ファイル | 変更内容 |
|----------|----------|
| `frontend/src/layouts/default.vue` | `provide('openAnalysis', openAnalysis)` の追加 |
| `frontend/src/components/Start.vue` | `inject('openAnalysis')`、Get Started カードの `@click` / `role` / `tabindex` / `@keydown`、必要に応じてスタイル |
| `frontend/src/locales/*.json` | （任意）`startPage.pressAnalysis` の文言調整 |

この手順に沿って実装すれば、パネルクリックで Analysis を開く直感的な挙動にできます。
