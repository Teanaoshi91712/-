# Personal Investment Management System (PIMS) - Design Review

## 1. 現状分析
現在のリポジトリを確認したところ、投資管理システムに関するコードベースは存在しません。
事実として、リポジトリ内には「柴燈護摩」に関する紙芝居風の静的HTMLファイル（`index.html`）および画像ディレクトリへの参照のみが存在しており、バックエンド、AIエージェント、Pythonスクリプトなどは一切存在していません。
したがって、今回のPersonal Investment Management System（PIMS）の構築は、事実上ゼロからの新規開発となります。

## 2. 目的
個人投資家が機関投資家の投資意思決定プロセスを参考にできる、一貫した投資プロセスを実現するシステムの構築。
単なる「AIのおすすめ」ではなく、情報収集、リサーチ、バリュエーション、リスク分析、ポートフォリオ構築、モニタリング、アトリビューションといったプロのフローをAIとPythonエンジン、そして人間の協調によって実現することが目的です。

## 3. 課題
- **ゼロベースからの構築:** 既存コードが存在しないため、インフラ、データベース、Python計算エンジン、Agent基盤などの全レイヤーの構築が必要です。
- **計算と推論の分離:** LLMに数値計算をさせず、Python側に計算処理（財務指標、リスク指標）を担わせるアーキテクチャの徹底。
- **人間の最終判断の担保:** AIによる自動発注を完全に排除し、「CIOの提案 → トレードプラン → 人間によるレビューと発注」のフローをシステム的に強制する仕組み作り。
- **コスト・パフォーマンスの最適化:** 多数の銘柄やニュースを処理する際のLLM APIコストと実行時間の抑制。

## 4. Issue
- **[ASSUMPTION] データベースおよびバックエンド基盤の選定と構築:** 現状コードが存在しないため、データ永続化層（PostgreSQLやSQLiteなどのRDBを想定）と、エージェントを動かすためのフレームワーク（LangChain, LlamaIndex, または軽量な自作基盤）の選定・構築が必要です。
- **[ASSUMPTION] 証券会社非連携での約定管理UXの確立:** APIを通じた自動発注を行わないため、ユーザーが証券会社で手動発注した後の結果を、システムへいかに入力しやすくするかがUX上のIssueとなります。
- **[ASSUMPTION] エージェント間通信プロトコルの定義:** 自由文ではなくJSON Schemaでエージェント間のInput/Outputを構造化するため、明確なスキーマ定義（Pydantic等の利用）が初期段階で不可欠です。

## 5. 推奨Architecture
**[ASSUMPTION]** 以下のアーキテクチャを推奨します。
- **Core System (Python):** 全体のフロー制御と、Quant Engine（財務指標・リスク計算等）を担当。複雑なMicroservicesを避け、MonolithicなPythonバックエンドとして構築。
- **Agent Orchestrator:** 各Agentのワークフローを管理。State Machine（例えばLangGraphや自前のステート管理機構）を用いて、Opportunity → Screening → Research → Valuation → Risk → CIO Reviewのフローを制御。
- **Model Adapter:** OpenAI, Anthropic, Gemini, Local Modelsを切り替え可能な共通インターフェース。直接ベンダーAPIを叩くのではなく、このAdapterを経由してコストやレイテンシのロギングを行います。
- **Database (Relational):** 財務データ、ポートフォリオ、監査ログ、Agent Run結果などを保存。整合性が重要なためRDB（PostgreSQL等）を推奨。

## 6. Agent一覧
マスタープロンプトの指定に基づき、以下のエージェントを定義します。
- CIO Agent
- Research Agent
- Valuation Agent
- Risk Agent
- Bull Agent
- Bear Agent
- Monitoring Agent
- Attribution Agent

※ Quant / Trade Planner / Execution はAgent化せず、Pythonのロジックとして実装。

## 7. Agent責務
- **CIO Agent:** システム統括。他エージェントの分析結果の統合、矛盾検出、最終的な投資判断案の作成、Trade Planへの指示。
- **Research Agent:** 決算書やニュースなどの定性情報から、FACT / INTERPRETATION / HYPOTHESIS / UNKNOWN / SOURCEを区別して抽出・分析。
- **Valuation Agent:** Python Engineが計算した指標（PER, PBR, DCF等）を受け取り、株価水準としての「解釈」を担当。
- **Risk Agent:** ポートフォリオ全体のリスク（Concentration, Beta, Volatility等）について、Python Engineの計算結果をもとに解釈・警告を実施。
- **Bull / Bear Agent:** 投資判断のポジティブ／ネガティブ双方の極端なケースや破綻シナリオを検証。
- **Monitoring Agent:** 保有銘柄の定期監視（株価・ニュース）。重要変化検出時にCIOへ再評価を要求。
- **Attribution Agent:** 投資結果（リターン）を分析し、要因（Security Selection, Valuation, Timing等）を分解・評価。

## 8. Model Strategy
**[ASSUMPTION]** 適材適所のモデルアサイン戦略を採用します。
- **高性能 (GPT-4o, Claude 3.5 Sonnet 等):** CIO, Attribution
- **中性能 (GPT-4o-mini, Claude 3.5 Haiku 等):** Research, Valuation, Bull, Bear
- **軽量/高速 (ローカルモデル or APIの最軽量モデル):** 情報のClassification, Extraction, 日次Monitoringの初期フィルタリング
- **LLM不使用:** Quant Engine, Trade Planner, 証券会社からの結果手動入力後のPortfolio更新処理

ベンダー非依存のModel Adapterを実装し、全推論で利用モデル、Token数、コストを記録します。

## 9. Data Architecture
**[ASSUMPTION]** ドメイン駆動で以下のエンティティを中心にRDBを設計します。
- **Market & Financial:** `Company`, `FinancialData`, `MarketData`, `News`
- **Investment Process:** `Research`, `InvestmentThesis`, `Valuation`, `RiskAnalysis`, `Decision`
- **Portfolio & Execution:** `Portfolio`, `Position`, `TradePlan`, `ExecutionResult`
- **System & Tracking:** `AgentRun`, `MonitoringEvent`, `Attribution`, `AuditLog`

すべての重要データに対して、`source`, `source_type`, `retrieved_at`, `confidence` などのメタデータを付与し、情報源がトレースできないものは事実とみなさない制約をスキーマ・ロジックレベルで担保します。

## 10. Security
- **Human-in-the-loop:** 「AIが提案し、人間が承認・発注する」フローの徹底。自動発注APIコードは含めない。
- **Secrets Management:** `.env`や環境変数を利用し、API Keyはコードに直書きしない（`.gitignore`の徹底）。
- **Auditability:** `AuditLog` テーブルに、timestamp, agent, model, decision, confidence, sources, prompt_version などを不変（Immutable）ログとして記録。
- **最小権限:** DBへのアクセス権限、各Agentが実行できるツールの権限を最小限に絞る。

## 11. Cost Optimization
- **ファネル型スクリーニング:**
  - 4,000銘柄 → [Python Rule/Quant] → 1,000銘柄
  - 1,000銘柄 → [軽量LLM] → 300銘柄
  - 300銘柄 → [Research Agent (中性能)] → 50銘柄
  - 50銘柄 → [Valuation/Risk] → 10銘柄
  - 10銘柄 → [CIO Agent (高性能)] → 3銘柄（人間へ提案）
- **[ASSUMPTION] Caching:** 過去の企業情報抽出結果や、同日中の同一ニュースに対するResearch結果はDB/Redisにキャッシュし、LLM APIコールをスキップする仕組みを実装。

## 12. MVP Scope
**[ASSUMPTION]** ゼロからの構築であることを踏まえ、MVP（Minimum Viable Product）では以下にスコープを限定します。
1. **コアデータモデルとバックエンドの構築**（DBスキーマ、Model Adapter、Agent間通信用Pydanticスキーマ）
2. **Python Quant Engine**（最低限の財務指標・ポートフォリオ計算）
3. **CIO, Research, Valuation Agentの実装**（中核となる意思決定フローの確立）
4. **Trade Plannerと手動入力UI/CLI**（発注案の出力と、ユーザーによる約定結果入力フロー）
※ Risk, Bull/Bear, Monitoring, Attributionは後続フェーズ（Phase 5以降）に回す。

## 13. Implementation Roadmap
1. **Phase 1: Data Model / Database** (DBスキーマ定義、ORM設定、基礎CRUD)
2. **Phase 2: Python Financial Engine** (指標計算用Quantロジック、Model Adapter実装)
3. **Phase 3: Research Agent** (企業情報等のLLM分析・JSON出力)
4. **Phase 4: Valuation Agent** (Quant Engine + LLM解釈)
5. **Phase 6: CIO Agent** (情報統合・意思決定ロジック) ※MVPにおける最重要機能
6. **Phase 8 & 9: Trade Planner & Human Execution** (プラン出力と約定入力)
7. **Phase 5 & 7: Risk / Bull / Bear Agents**
8. **Phase 10 & 11: Monitoring & Attribution**
※ 複雑化を避けるため、フェーズごとに「本当にAgentが必要か（Pythonで十分か）」を再検証しながら進める。

## 14. 技術的リスク
- **[ASSUMPTION] LLMのJSON出力の安定性:** Agent間通信で厳密なJSON Schemaを要求するが、LLMがスキーマ違反の出力をするリスク。対策として、リトライ機構やPydanticベースのValidation + 修正プロンプトの導入が必要。
- **[ASSUMPTION] データソースの確保:** 財務データ、ニュースデータ等の信頼できるデータフィード（API）を低コストで確保できるか。
- **[ASSUMPTION] 過剰な抽象化:** マルチエージェントフレームワーク（AutoGen, CrewAI等）を導入すると、処理フローがブラックボックス化し、本要件である「CIOによる段階的・厳密な制御」が難しくなるリスク。

## 15. 未決定事項
- **[ASSUMPTION] マルチエージェントの実装基盤:** 既存のLangGraph等のフレームワークを利用するか、要件に合わせてシンプルな関数/クラスベースの独自制御基盤を構築するか。推奨は後者（ブラックボックス化回避のため）。
- **[ASSUMPTION] 情報源APIの選定:** 企業の決算情報や株価等を取得する外部APIプロバイダ（Yahoo Finance, Alpha Vantage, EDINET API等）の具体的な選定。
- **[ASSUMPTION] UI/UXの形態:** MVPはCLIベースとするか、初期からStreamlit/Gradio等でWebUIを持たせるか。

## 16. 推奨Next Action
1. **本設計レビューの承認:** 本レビュー内容（特にAgent分割、CIO設計、データモデル、LLM/Python境界、MVPスコープ）についてユーザーのフィードバック・承認を得る。
2. **技術選定の確定（特にAgentフレームワークとUI要件）:** MVPをCLIで進めるか、フレームワークをどうするかを決定。
3. **Phase 1 (Data Model) の着手:** 承認後、最初のコードとしてDBスキーマとPydanticモデル（Agent間の通信I/O定義）の実装を開始する。
