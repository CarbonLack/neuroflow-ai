from __future__ import annotations

import json
import os
import uuid
from collections.abc import Callable
from dataclasses import replace
from html import escape
from typing import Any

from PySide6.QtCore import QSettings, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .ai import (
    STAGE_LABELS,
    AIResponse,
    AISettings,
    build_project_summary,
    redact_sensitive_text,
    request_ai_advice,
)
from .models import ProjectState


def load_ai_settings() -> AISettings:
    store = QSettings("NeuroFlow", "NeuroFlow")
    store.beginGroup("ai")
    installation_id = str(store.value("installation_id", "") or "")
    if not installation_id:
        installation_id = f"nf_{uuid.uuid4().hex}"
        store.setValue("installation_id", installation_id)
    settings = AISettings(
        provider=str(store.value("provider", "openai_responses")),
        base_url=str(store.value("base_url", "https://api.openai.com/v1")),
        model=str(store.value("model", "gpt-5.6-terra")),
        reasoning_effort=str(store.value("reasoning_effort", "medium")),
        timeout_seconds=int(store.value("timeout_seconds", 90)),
        include_recent_log=(
            str(store.value("include_recent_log", "false")).lower() == "true"
        ),
        safety_identifier=installation_id,
        api_key=os.environ.get("OPENAI_API_KEY", ""),
    )
    store.endGroup()
    return settings


def save_ai_preferences(settings: AISettings) -> None:
    """Persist non-secret preferences. API keys intentionally remain in memory."""
    store = QSettings("NeuroFlow", "NeuroFlow")
    store.beginGroup("ai")
    store.setValue("provider", settings.provider)
    store.setValue("base_url", settings.base_url)
    store.setValue("model", settings.model)
    store.setValue("reasoning_effort", settings.reasoning_effort)
    store.setValue("timeout_seconds", settings.timeout_seconds)
    store.setValue("include_recent_log", settings.include_recent_log)
    store.setValue("installation_id", settings.safety_identifier)
    store.endGroup()


class AIWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        settings: AISettings,
        *,
        question: str,
        task: str,
        language: str,
        project_summary: dict[str, Any],
        history: list[dict[str, str]],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.settings = replace(settings)
        self.question = question
        self.task = task
        self.language = language
        self.project_summary = project_summary
        self.history = history

    def run(self) -> None:
        try:
            response = request_ai_advice(
                self.settings,
                question=self.question,
                task=self.task,
                language=self.language,
                project_summary=self.project_summary,
                history=self.history,
            )
            self.completed.emit(response)
        except Exception as exc:  # noqa: BLE001 - remote boundary
            self.failed.emit(redact_sensitive_text(str(exc)))


class AISettingsDialog(QDialog):
    def __init__(
        self,
        settings: AISettings,
        language: str,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.language = language
        self.settings = replace(settings)
        self.setWindowTitle(
            "AI assistant settings"
            if language == "en_US"
            else "AI 助手设置"
        )
        self.setMinimumWidth(720)

        layout = QVBoxLayout(self)
        intro = QLabel(
            (
                "The model runs in the cloud. NeuroFlow sends only the previewed "
                "structured summary; raw voltage and local paths stay on this computer."
            )
            if language == "en_US"
            else (
                "模型在云端运行。NeuroFlow 只发送可预览的结构化摘要；"
                "原始电压和本地路径始终留在当前电脑。"
            )
        )
        intro.setWordWrap(True)
        intro.setObjectName("Muted")
        layout.addWidget(intro)

        form = QFormLayout()
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("OpenAI Responses API", "openai_responses")
        self.provider_combo.addItem(
            "OpenAI-compatible Chat API",
            "openai_compatible",
        )
        self.provider_combo.setCurrentIndex(
            max(self.provider_combo.findData(settings.provider), 0)
        )
        form.addRow(
            "Provider" if language == "en_US" else "服务方式",
            self.provider_combo,
        )

        self.base_url_edit = QLineEdit(settings.base_url)
        self.base_url_edit.setPlaceholderText("https://api.openai.com/v1")
        form.addRow(
            "API base URL" if language == "en_US" else "API 地址",
            self.base_url_edit,
        )

        self.model_edit = QComboBox()
        self.model_edit.setEditable(True)
        self.model_edit.addItems(
            ["gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.6-sol"]
        )
        self.model_edit.setCurrentText(settings.model)
        form.addRow(
            "Model" if language == "en_US" else "模型",
            self.model_edit,
        )

        self.reasoning_combo = QComboBox()
        for value in ("none", "low", "medium", "high", "xhigh"):
            self.reasoning_combo.addItem(value, value)
        self.reasoning_combo.setCurrentIndex(
            max(
                self.reasoning_combo.findData(settings.reasoning_effort),
                0,
            )
        )
        form.addRow(
            "Reasoning effort" if language == "en_US" else "推理强度",
            self.reasoning_combo,
        )

        key_row = QHBoxLayout()
        self.api_key_edit = QLineEdit(settings.api_key)
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText(
            "OPENAI_API_KEY"
            if language == "en_US"
            else "粘贴 API 密钥"
        )
        self.show_key = QCheckBox(
            "Show" if language == "en_US" else "显示"
        )
        self.show_key.toggled.connect(
            lambda checked: self.api_key_edit.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        key_row.addWidget(self.api_key_edit, 1)
        key_row.addWidget(self.show_key)
        key_widget = QWidget()
        key_widget.setLayout(key_row)
        form.addRow(
            "API key" if language == "en_US" else "API 密钥",
            key_widget,
        )

        self.include_log_check = QCheckBox(
            
                "Include the five most recent audit-log messages"
                if language == "en_US"
                else "同时发送最近 5 条审计日志"
            
        )
        self.include_log_check.setChecked(settings.include_recent_log)
        form.addRow(
            "Additional context" if language == "en_US" else "额外上下文",
            self.include_log_check,
        )
        layout.addLayout(form)

        key_note = QLabel(
            (
                "The API key is not written to the project or application settings. "
                "It is kept only for this running NeuroFlow session. You can also set "
                "the OPENAI_API_KEY environment variable."
            )
            if language == "en_US"
            else (
                "API 密钥不会写入项目或软件设置，只在本次 NeuroFlow 运行期间"
                "保存在内存中；也可以通过 OPENAI_API_KEY 环境变量提供。"
            )
        )
        key_note.setWordWrap(True)
        key_note.setObjectName("Muted")
        layout.addWidget(key_note)

        recommendation = QLabel(
            (
                "Recommended starting point: Responses API + gpt-5.6-terra + medium. "
                "Use Luna when cost and response speed matter more. Custom or private "
                "OpenAI-compatible services can use the Chat API option."
            )
            if language == "en_US"
            else (
                "推荐起点：Responses API + gpt-5.6-terra + medium。更在意成本和"
                "速度时可选 Luna；自定义或私有 OpenAI 兼容服务可选择 Chat API。"
            )
        )
        recommendation.setWordWrap(True)
        recommendation.setObjectName("InsetPanel")
        recommendation.setContentsMargins(12, 9, 12, 9)
        layout.addWidget(recommendation)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Cancel | QDialogButtonBox.Save
        )
        buttons.button(QDialogButtonBox.Save).setText(
            "Apply settings" if language == "en_US" else "应用设置"
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        self.settings.provider = str(self.provider_combo.currentData())
        self.settings.base_url = self.base_url_edit.text().strip()
        self.settings.model = self.model_edit.currentText().strip()
        self.settings.reasoning_effort = str(
            self.reasoning_combo.currentData()
        )
        self.settings.api_key = self.api_key_edit.text().strip()
        self.settings.include_recent_log = self.include_log_check.isChecked()
        if not self.settings.base_url or not self.settings.model:
            QMessageBox.warning(
                self,
                "Incomplete settings"
                if self.language == "en_US"
                else "设置不完整",
                (
                    "Enter an API address and model."
                    if self.language == "en_US"
                    else "请填写 API 地址和模型。"
                ),
            )
            return
        save_ai_preferences(self.settings)
        self.accept()


class ContextPreviewDialog(QDialog):
    def __init__(
        self,
        summary: dict[str, Any],
        language: str,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(
            "Cloud data preview"
            if language == "en_US"
            else "云端发送内容预览"
        )
        self.resize(820, 650)
        layout = QVBoxLayout(self)
        explanation = QLabel(
            (
                "This is the complete project summary supplied with the next AI "
                "request. Your question and recent AI conversation are added separately."
            )
            if language == "en_US"
            else (
                "这是下一次 AI 请求会携带的完整项目摘要；你的问题和最近的 AI "
                "对话会单独附加。"
            )
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        viewer = QPlainTextEdit()
        viewer.setReadOnly(True)
        viewer.setPlainText(
            json.dumps(summary, ensure_ascii=False, indent=2)
        )
        layout.addWidget(viewer, 1)
        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)


class AIAssistantDialog(QDialog):
    def __init__(
        self,
        *,
        state_getter: Callable[[], ProjectState | None],
        stage_getter: Callable[[], str],
        language_getter: Callable[[], str],
        response_handler: Callable[[AIResponse, str, str], None],
        plan_handler: Callable[[list[dict[str, Any]], str], None],
        manual_handler: Callable[[], None],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.state_getter = state_getter
        self.stage_getter = stage_getter
        self.language_getter = language_getter
        self.response_handler = response_handler
        self.plan_handler = plan_handler
        self.manual_handler = manual_handler
        self.settings = load_ai_settings()
        self.history: list[dict[str, str]] = []
        self.current_plan: list[dict[str, Any]] = []
        self.current_next_stage = "import"
        self.worker: AIWorker | None = None
        self.loaded_project_token = ""

        self.resize(1280, 790)
        self.setMinimumSize(1050, 680)
        self.setModal(False)
        self._build_ui()
        self.set_language(self.language_getter())

    def load_project_history(
        self,
        records: list[dict[str, Any]],
        project_token: str,
    ) -> None:
        if project_token == self.loaded_project_token:
            return
        self.loaded_project_token = project_token
        self.history = []
        self.conversation.clear()
        for record in records[-6:]:
            question = str(record.get("question", "")).strip()
            answer = str(record.get("answer", "")).strip()
            if question:
                self.history.append({"role": "user", "content": question})
                self._append_message("user", question)
            if answer:
                self.history.append({"role": "assistant", "content": answer})
                self._append_message("assistant", answer)
        self.history = self.history[-12:]

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 22px; font-weight: 700;")
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("Muted")
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.subtitle_label)
        header.addLayout(title_box)
        header.addStretch()
        self.context_button = QPushButton()
        self.context_button.clicked.connect(self._show_context)
        self.manual_button = QPushButton()
        self.manual_button.clicked.connect(self.manual_handler)
        self.settings_button = QPushButton()
        self.settings_button.clicked.connect(self._open_settings)
        header.addWidget(self.context_button)
        header.addWidget(self.manual_button)
        header.addWidget(self.settings_button)
        root.addLayout(header)

        self.status_frame = QFrame()
        self.status_frame.setObjectName("InsetPanel")
        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(12, 8, 12, 8)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label, 1)
        root.addWidget(self.status_frame)

        body = QHBoxLayout()
        body.setSpacing(12)

        chat_frame = QFrame()
        chat_frame.setObjectName("Card")
        chat_layout = QVBoxLayout(chat_frame)
        chat_layout.setContentsMargins(12, 12, 12, 12)
        self.quick_title = QLabel()
        self.quick_title.setStyleSheet("font-weight: 700;")
        chat_layout.addWidget(self.quick_title)
        quick_row = QHBoxLayout()
        self.explain_button = QPushButton()
        self.review_button = QPushButton()
        self.plan_button = QPushButton()
        self.error_button = QPushButton()
        self.explain_button.clicked.connect(
            lambda: self._quick_request("explain")
        )
        self.review_button.clicked.connect(
            lambda: self._quick_request("review")
        )
        self.plan_button.clicked.connect(
            lambda: self._quick_request("plan")
        )
        self.error_button.clicked.connect(
            lambda: self._quick_request("error")
        )
        for button in (
            self.explain_button,
            self.review_button,
            self.plan_button,
            self.error_button,
        ):
            quick_row.addWidget(button)
        chat_layout.addLayout(quick_row)

        self.conversation = QTextBrowser()
        self.conversation.setOpenExternalLinks(False)
        chat_layout.addWidget(self.conversation, 1)

        self.question_edit = QPlainTextEdit()
        self.question_edit.setMaximumHeight(105)
        chat_layout.addWidget(self.question_edit)
        send_row = QHBoxLayout()
        self.privacy_label = QLabel()
        self.privacy_label.setObjectName("Muted")
        self.privacy_label.setWordWrap(True)
        send_row.addWidget(self.privacy_label, 1)
        self.send_button = QPushButton()
        self.send_button.setObjectName("Primary")
        self.send_button.setMinimumWidth(150)
        self.send_button.clicked.connect(lambda: self._submit("ask"))
        send_row.addWidget(self.send_button)
        chat_layout.addLayout(send_row)
        body.addWidget(chat_frame, 3)

        plan_frame = QFrame()
        plan_frame.setObjectName("Card")
        plan_frame.setMinimumWidth(700)
        plan_layout = QVBoxLayout(plan_frame)
        plan_layout.setContentsMargins(12, 12, 12, 12)
        self.plan_title = QLabel()
        self.plan_title.setStyleSheet("font-weight: 700;")
        plan_layout.addWidget(self.plan_title)
        self.plan_explanation = QLabel()
        self.plan_explanation.setWordWrap(True)
        self.plan_explanation.setObjectName("Muted")
        plan_layout.addWidget(self.plan_explanation)
        self.plan_table = QTableWidget(0, 4)
        self.plan_table.verticalHeader().setVisible(False)
        self.plan_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.plan_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.plan_table.setWordWrap(True)
        plan_header = self.plan_table.horizontalHeader()
        plan_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        plan_header.setSectionResizeMode(1, QHeaderView.Stretch)
        plan_header.setSectionResizeMode(2, QHeaderView.Stretch)
        plan_header.setSectionResizeMode(3, QHeaderView.Stretch)
        plan_layout.addWidget(self.plan_table, 1)
        self.apply_plan_button = QPushButton()
        self.apply_plan_button.setEnabled(False)
        self.apply_plan_button.clicked.connect(self._apply_plan)
        plan_layout.addWidget(self.apply_plan_button)
        body.addWidget(plan_frame, 2)
        root.addLayout(body, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.hide)
        root.addWidget(buttons)
        self.close_buttons = buttons

    def set_language(self, language: str) -> None:
        english = language == "en_US"
        self.setWindowTitle(
            "NeuroFlow AI assistant" if english else "NeuroFlow AI 助手"
        )
        self.title_label.setText(
            "NeuroFlow AI assistant" if english else "NeuroFlow AI 助手"
        )
        self.subtitle_label.setText(
            (
                "Advisory only: understand the question, inspect the summary, and "
                "propose a reviewable plan"
            )
            if english
            else "只做辅助：理解问题、审查摘要、提出可审核的候选方案"
        )
        self.context_button.setText(
            "Preview cloud data" if english else "预览云端发送内容"
        )
        self.manual_button.setText(
            "AI manual" if english else "AI 操作手册"
        )
        self.settings_button.setText(
            "AI settings" if english else "AI 设置"
        )
        self.quick_title.setText(
            "Start from a defined task" if english else "从明确任务开始"
        )
        self.explain_button.setText(
            "Explain this stage" if english else "解释当前阶段"
        )
        self.review_button.setText(
            "Review project" if english else "审查当前项目"
        )
        self.plan_button.setText(
            "Propose workflow" if english else "生成候选流程"
        )
        self.error_button.setText(
            "Explain latest error" if english else "解释最近异常"
        )
        self.question_edit.setPlaceholderText(
            (
                "Describe your scientific question or ask about a parameter. "
                "The model receives the previewed summary, not raw voltage."
            )
            if english
            else (
                "描述你的科学问题，或询问某个参数。模型只会收到预览中的摘要，"
                "不会收到原始电压。"
            )
        )
        self.privacy_label.setText(
            (
                "Raw signal and local paths are never sent. AI cannot run an analysis "
                "without your confirmation."
            )
            if english
            else "不发送原始信号和本地路径；AI 未经确认不能运行分析。"
        )
        self.send_button.setText("Ask AI" if english else "询问 AI")
        self.plan_title.setText(
            "Reviewable workflow plan" if english else "可审核的候选工作流"
        )
        self.plan_explanation.setText(
            (
                "A plan is advice, not an executed workflow. Applying it stores the "
                "plan in the project and moves to the suggested stage; it does not run."
            )
            if english
            else (
                "候选流程只是建议，并未执行。应用后只会将方案存入项目并跳转到"
                "建议阶段，不会自动运行。"
            )
        )
        self.plan_table.setHorizontalHeaderLabels(
            ["Stage", "Why", "Pre-\nrequisites", "Recommended\nparameters"]
            if english
            else ["阶段", "为什么做", "前提条件", "参数建议"]
        )
        self.apply_plan_button.setText(
            "Apply plan to project" if english else "将方案应用到项目"
        )
        self.close_buttons.button(QDialogButtonBox.Close).setText(
            "Close" if english else "关闭"
        )
        self._refresh_status()
        self._render_plan()

    def _refresh_status(self) -> None:
        english = self.language_getter() == "en_US"
        if self.settings.configured:
            self.status_label.setText(
                (
                    f"Ready · {self.settings.provider_label} · "
                    f"{self.settings.model} · key held in memory only"
                )
                if english
                else (
                    f"已就绪 · {self.settings.provider_label} · "
                    f"{self.settings.model} · 密钥仅保存在内存"
                )
            )
        else:
            self.status_label.setText(
                (
                    "Cloud AI is not configured. Open AI settings and enter an API "
                    "key; manual and guided analysis remain fully available."
                )
                if english
                else (
                    "尚未配置云端 AI。请打开 AI 设置并填写 API 密钥；"
                    "手动和引导式分析仍可完整使用。"
                )
            )

    def _summary(self) -> dict[str, Any]:
        return build_project_summary(
            self.state_getter(),
            self.stage_getter(),
            include_recent_log=self.settings.include_recent_log,
        )

    def _show_context(self) -> None:
        ContextPreviewDialog(
            self._summary(),
            self.language_getter(),
            self,
        ).exec()

    def _open_settings(self) -> None:
        dialog = AISettingsDialog(
            self.settings,
            self.language_getter(),
            self,
        )
        if dialog.exec() == QDialog.Accepted:
            self.settings = dialog.settings
            self._refresh_status()

    def _quick_request(self, task: str) -> None:
        english = self.language_getter() == "en_US"
        prompts = {
            "explain": (
                "Explain the scientific purpose of the current stage, what I should "
                "inspect, which parameters matter, and what evidence is needed before "
                "continuing."
                if english
                else (
                    "请解释当前阶段的科学目的、我应该检查什么、哪些参数最重要，"
                    "以及进入下一阶段前需要具备什么证据。"
                )
            ),
            "review": (
                "Review the current project status. Identify completed evidence, "
                "missing prerequisites, risks, and the safest next action."
                if english
                else (
                    "请审查当前项目状态，区分已有证据、缺失前提、主要风险，"
                    "并给出最稳妥的下一步。"
                )
            ),
            "plan": (
                "Propose a complete but focused analysis workflow for this recording. "
                "Explain every stage, prerequisites, and parameter starting points. "
                "Do not claim that any proposed step has run."
                if english
                else (
                    "请针对当前记录提出一条完整但聚焦的分析流程，说明每个阶段的"
                    "目的、前提和参数起点；不要把建议步骤说成已经运行。"
                )
            ),
            "error": (
                "Explain the latest available failure or warning in the project summary. "
                "Separate data, environment, parameter, and scientific risks, then give "
                "non-destructive troubleshooting steps."
                if english
                else (
                    "请解释项目摘要中最近的失败或警告，区分数据、环境、参数和"
                    "科学风险，并给出不破坏已有结果的排查步骤。"
                )
            ),
        }
        self.question_edit.setPlainText(prompts[task])
        self._submit(task)

    def _submit(self, task: str) -> None:
        if self.worker and self.worker.isRunning():
            return
        question = self.question_edit.toPlainText().strip()
        if not question:
            return
        if not self.settings.configured:
            self._open_settings()
            if not self.settings.configured:
                return
        language = self.language_getter()
        self._append_message("user", question)
        self.history.append({"role": "user", "content": question})
        self._set_running(True)
        self.worker = AIWorker(
            self.settings,
            question=question,
            task=task,
            language=language,
            project_summary=self._summary(),
            history=self.history[:-1],
            parent=self,
        )
        self.worker.completed.connect(
            lambda response: self._on_completed(response, question, task)
        )
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _set_running(self, running: bool) -> None:
        for button in (
            self.send_button,
            self.explain_button,
            self.review_button,
            self.plan_button,
            self.error_button,
            self.settings_button,
        ):
            button.setEnabled(not running)
        english = self.language_getter() == "en_US"
        if running:
            self.status_label.setText(
                
                    "Waiting for cloud AI; NeuroFlow remains unchanged..."
                    if english
                    else "正在等待云端 AI；NeuroFlow 项目尚未发生任何修改……"
                
            )
        else:
            self._refresh_status()

    def _append_message(self, role: str, text: str) -> None:
        english = self.language_getter() == "en_US"
        label = (
            ("You" if english else "你")
            if role == "user"
            else ("AI advisory response" if english else "AI 辅助建议")
        )
        color = "#1f7a63" if role == "assistant" else "#33433d"
        body = escape(text).replace("\n", "<br>")
        self.conversation.append(
            f'<div style="margin:8px 0 14px 0;">'
            f'<b style="color:{color};">{escape(label)}</b><br>'
            f'<span style="line-height:1.45;">{body}</span></div>'
        )

    def _on_completed(
        self,
        response: AIResponse,
        question: str,
        task: str,
    ) -> None:
        self._set_running(False)
        self.history.append({"role": "assistant", "content": response.answer})
        self.history = self.history[-12:]
        rendered = response.answer
        if response.warnings:
            heading = (
                "Warnings to review"
                if self.language_getter() == "en_US"
                else "需要复核的警告"
            )
            rendered += "\n\n" + heading + ":\n- " + "\n- ".join(
                response.warnings
            )
        self._append_message("assistant", rendered)
        self.current_plan = response.plan
        self.current_next_stage = response.suggested_next_stage
        self._render_plan()
        self.response_handler(response, question, task)

    def _on_failed(self, details: str) -> None:
        self._set_running(False)
        english = self.language_getter() == "en_US"
        QMessageBox.critical(
            self,
            "AI request failed" if english else "AI 请求失败",
            (
                f"{details}\n\nThe project was not changed. Check the endpoint, model, "
                "API key, network, and account quota."
                if english
                else (
                    f"{details}\n\n项目未被修改。请检查 API 地址、模型、密钥、"
                    "网络和账户额度。"
                )
            ),
        )

    def _render_plan(self) -> None:
        language = self.language_getter()
        self.plan_table.setRowCount(len(self.current_plan))
        for row, item in enumerate(self.current_plan):
            parameters = "\n".join(
                f"{entry['name']} = {entry['value']}: {entry['rationale']}"
                for entry in item.get("recommended_parameters", [])
            )
            values = (
                STAGE_LABELS[language].get(item["stage"], item["stage"]),
                item.get("reason", ""),
                "\n".join(item.get("prerequisites", [])),
                parameters,
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value or "—")
                cell.setToolTip(value)
                self.plan_table.setItem(row, column, cell)
        self.plan_table.resizeRowsToContents()
        self.apply_plan_button.setEnabled(bool(self.current_plan))

    def _apply_plan(self) -> None:
        if not self.current_plan:
            return
        self.plan_handler(self.current_plan, self.current_next_stage)
