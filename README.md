# GenieGuard: World-Sim CI

**AI生成シミュレータの「出荷前」自動監査・自己修復・再検証を回す閉ループCIエージェント**

## Quick Start

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 開発サーバーの起動

```bash
python server.py
```

ブラウザで http://localhost:8080 が開きます。

### 3. デモの実行

**方法A: ダッシュボードUI**
```bash
python server.py --dashboard
```
「Random Break」→「Run GenieGuard」の順にクリック

**方法B: CLI**
```bash
# ランダムに壊す
python break.py

# GenieGuardを実行（自動検知・修復・検証）
python genieguard.py --no-break

# または一括実行（破壊から検証まで）
python genieguard.py
```

## プロジェクト構成

```
0221a/
├── web/                    # Webシミュレータ
│   ├── index.html          # シミュレータUI
│   ├── dashboard.html      # デモダッシュボード
│   ├── sim.js              # Matter.js物理シミュレーション
│   ├── config.js           # 物理パラメータ（修復対象）
│   ├── telemetry.js        # テレメトリシステム
│   └── hud.js              # HUDオーバーレイ
│
├── genieguard/             # Pythonモジュール
│   ├── random_breaker.py   # ランダム破壊
│   ├── telemetry_collector.py  # テレメトリ収集
│   ├── invariant_checker.py    # 数値判定（VLM非依存）
│   ├── patch_selector.py   # LLMパッチ選択
│   ├── patch_applier.py    # パッチ適用
│   └── evidence_exporter.py    # 証跡出力
│
├── data/
│   └── patch_catalog.json  # パッチカタログ
│
├── output/                 # 出力ディレクトリ
│   ├── audit_report.json   # 監査レポート
│   ├── patch.diff          # 修正差分
│   ├── before.png          # 修正前スクショ
│   ├── after.png           # 修正後スクショ
│   ├── ci_result.txt       # CI結果
│   └── run_log.txt         # 実行ログ
│
├── genieguard.py           # メインCLI
├── break.py                # 破壊スクリプト
├── server.py               # 開発サーバー
└── requirements.txt        # 依存関係
```

## バグ種類（5種類）

| ID | バグ名 | 破壊内容 | 可視化される破綻 |
|----|--------|----------|------------------|
| B1 | 重力反転 | gravityY = -1 | ボールが上に飛ぶ |
| B2 | 衝突無効化 | collisionMask = 0 | 床をすり抜ける |
| B3 | 反発係数異常 | restitution = 5.0 | バウンスで加速 |
| B4 | 摩擦消失 | friction = 0 | 永遠に滑り続ける |
| B5 | 境界無効 | boundsEnabled = false | 画面外に消える |

## 設計原則

1. **テレメトリ主導判定** - PASS/FAILは数値条件で判定。VLMに依存しない
2. **パッチカタログ方式** - LLMはpatch_idを選択するのみ。コード生成させない
3. **スクショは証跡のみ** - 画像は保存用。判定には使わない
4. **ランダム破壊** - 5種類バグから1〜3個をランダム選択

## CLIオプション

```bash
# フルパイプライン（破壊→検知→修復→検証）
python genieguard.py

# 破壊スキップ（現状をテスト）
python genieguard.py --no-break

# 特定バグを注入
python genieguard.py --specific B1 B3

# バグ数を指定
python genieguard.py --bugs 2

# ヘッドレスモード
python genieguard.py --headless
```

## 環境変数

```bash
# Gemini APIキー（オプション - なくてもフォールバックで動作）
export GEMINI_API_KEY=your_api_key
# または
export GOOGLE_API_KEY=your_api_key
```

## 出力成果物

| ファイル | 内容 | 用途 |
|----------|------|------|
| audit_report.json | 検知バグ一覧、テレメトリ要約、適用パッチ | 監査証跡 |
| patch.diff | config.jsの差分 | 修正証拠 |
| before.png | 修正前スクリーンショット | ビジュアル比較 |
| after.png | 修正後スクリーンショット | ビジュアル比較 |
| ci_result.txt | PASS/FAIL + 各条件の判定結果 | CIゲート |
| run_log.txt | 全実行ログ | デバッグ+再現 |

## ライセンス

MIT License
