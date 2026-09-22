from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Callable
from dataclasses import replace
from html import escape
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings, QThread, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QBoxLayout,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
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
    PROVIDER_PROFILES,
    build_project_summary,
    check_provider_health,
    redact_sensitive_text,
    request_ai_advice,
)
from .ai_credentials import get_api_key, store_api_key
from .ai_harness import discover_deepseek_harness_profiles
from .ai_conversations import (
    THREAD_GROUPS,
    create_thread,
    ensure_stage_thread,
    ensure_threads,
    group_label,
    load_general_conversations,
    matching_threads,
    record_in_thread,
    rename_thread,
    save_general_conversations,
    set_thread_group,
    thread_records,
)
from .chat_bubbles import BubbleChatView
from .ai_tools import AIMode, validate_tool_call
from .ai_project_bridge import ProjectQueries
from .ai_presentation import (
    build_readable_ai_view,
    full_response_html,
    readable_view_html,
)
from .models import ProjectState
from .product import PRODUCT_NAME


class ChatComposer(QPlainTextEdit):
    """Enter sends; Shift+Enter inserts a line break."""

    submitted = Signal()

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt API
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
            if not event.isAutoRepeat():
                self.submitted.emit()
            event.accept()
            return
        super().keyPressEvent(event)


def confirm_chart_attachment(image_png: bytes, language: str, parent: QWidget,
                             provider_label: str = "configured AI service") -> bool:
    """Preview the exact raster that will leave the computer before attaching it."""
    dialog = QDialog(parent)
    dialog.setWindowTitle("Attach current chart" if language == "en_US" else "附加当前图")
    dialog.resize(760, 650)
    dialog.setMinimumSize(420, 340)
    layout = QVBoxLayout(dialog)
    note = QLabel(
        f"This PNG image will be sent to {provider_label}. It may contain labels or visible raw traces. No other file is sent."
        if language == "en_US" else
        f"下方这张 PNG 将发送给 {provider_label}；图上可能包含文字或原始波形。不会发送其他文件。"
    )
    note.setWordWrap(True)
    layout.addWidget(note)
    preview = QLabel()
    preview.setAlignment(Qt.AlignCenter)
    pixmap = QPixmap()
    if not pixmap.loadFromData(image_png, "PNG"):
        return False
    preview.setPixmap(pixmap.scaled(700, 480, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(preview)
    layout.addWidget(scroll, 1)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.button(QDialogButtonBox.Ok).setText("Attach" if language == "en_US" else "确认附加")
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    return dialog.exec() == QDialog.Accepted


def _stored_json_list(value: Any) -> list[str]:
    try:
        parsed = json.loads(str(value or "[]"))
    except json.JSONDecodeError:
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def load_ai_settings() -> AISettings:
    store = QSettings(PRODUCT_NAME, PRODUCT_NAME)
    store.beginGroup("ai")
    installation_id = str(store.value("installation_id", "") or "")
    if not installation_id:
        installation_id = f"nf_{uuid.uuid4().hex}"
        store.setValue("installation_id", installation_id)
    settings = AISettings(
        provider=str(store.value("provider", "deepseek")),
        base_url=str(store.value("base_url", "https://api.deepseek.com")),
        model=str(store.value("model", "deepseek-v4-flash")),
        mode=str(store.value("mode", AIMode.ASSISTANT.value)),
        reasoning_effort=str(store.value("reasoning_effort", "medium")),
        timeout_seconds=int(store.value("timeout_seconds", 90)),
        retry_count=int(store.value("retry_count", 2)),
        stream=str(store.value("stream", "true")).lower() == "true",
        include_recent_log=(
            str(store.value("include_recent_log", "false")).lower() == "true"
        ),
        selected_context_fields=_stored_json_list(
            store.value("selected_context_fields", "[]")
        ),
        safety_identifier=installation_id,
        api_key_env=str(store.value("api_key_env", "")),
        allow_insecure_private_network=(
            str(
                store.value(
                    "allow_insecure_private_network",
                    "false",
                )
            ).lower()
            == "true"
        ),
        managed_harness_name=str(
            store.value("managed_harness_name", "")
        ),
        harness_provider=str(store.value("harness_provider", "")),
    )
    settings.api_key = "" if settings.provider == "harness_sdk" else get_api_key(
        settings.provider,
        settings.api_key_env,
    )
    store.endGroup()
    return settings


def save_ai_preferences(settings: AISettings) -> None:
    """Persist non-secret preferences. API keys intentionally remain in memory."""
    store = QSettings(PRODUCT_NAME, PRODUCT_NAME)
    store.beginGroup("ai")
    store.setValue("provider", settings.provider)
    store.setValue("base_url", settings.base_url)
    store.setValue("model", settings.model)
    store.setValue("mode", settings.mode)
    store.setValue("reasoning_effort", settings.reasoning_effort)
    store.setValue("timeout_seconds", settings.timeout_seconds)
    store.setValue("retry_count", settings.retry_count)
    store.setValue("stream", settings.stream)
    store.setValue("include_recent_log", settings.include_recent_log)
    store.setValue(
        "selected_context_fields",
        json.dumps(settings.selected_context_fields),
    )
    store.setValue("installation_id", settings.safety_identifier)
    store.setValue("api_key_env", settings.api_key_env)
    store.setValue(
        "allow_insecure_private_network",
        settings.allow_insecure_private_network,
    )
    store.setValue("managed_harness_name", settings.managed_harness_name)
    store.setValue("harness_provider", settings.harness_provider)
    store.endGroup()


def load_ai_reading_mode() -> str:
    store = QSettings(PRODUCT_NAME, PRODUCT_NAME)
    value = str(store.value("ai/reading_mode", "compact") or "compact")
    return value if value in {"compact", "full"} else "compact"


def save_ai_reading_mode(value: str) -> None:
    QSettings(PRODUCT_NAME, PRODUCT_NAME).setValue(
        "ai/reading_mode", "full" if value == "full" else "compact"
    )


class AIResponseDetailDialog(QDialog):
    def __init__(
        self,
        record: dict[str, Any],
        language: str = "zh_CN",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        english = language == "en_US"
        self.setWindowTitle(
            "AI answer details" if english else "AI 完整说明与依据"
        )
        self.resize(860, 680)
        self.setMinimumSize(500, 380)
        layout = QVBoxLayout(self)
        title = QLabel(
            "Full answer, evidence and limitations"
            if english
            else "完整回答、依据与限制"
        )
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(title)
        hint = QLabel(
            "This detail view preserves scientific context; the chat keeps only the decision-relevant summary."
            if english
            else "这里保留科研语境和技术细节；聊天区只显示当前决策真正需要的信息。"
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        viewer = QTextBrowser()
        viewer.setHtml(full_response_html(record, language))
        layout.addWidget(viewer, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Close).setText(
            "Close" if english else "关闭"
        )
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class AIWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    streamed = Signal(str)

    def __init__(
        self,
        settings: AISettings,
        *,
        question: str,
        task: str,
        language: str,
        project_summary: dict[str, Any],
        history: list[dict[str, str]],
        project_queries=None,
        image_png: bytes | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.settings = replace(settings)
        self.question = question
        self.task = task
        self.language = language
        self.project_summary = project_summary
        self.history = history
        self.project_queries = project_queries
        self.image_png = image_png
        self.cancel_event = threading.Event()

    def run(self) -> None:
        try:
            response = request_ai_advice(
                self.settings,
                question=self.question,
                task=self.task,
                language=self.language,
                project_summary=self.project_summary,
                history=self.history,
                on_stream_text=self.streamed.emit,
                cancel_event=self.cancel_event,
                project_queries=self.project_queries,
                image_png=self.image_png,
            )
            self.completed.emit(response)
        except Exception as exc:  # noqa: BLE001 - remote boundary
            self.failed.emit(redact_sensitive_text(str(exc)))

    def cancel(self) -> None:
        self.cancel_event.set()


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
        self.resize(760, 650)
        self.setMinimumSize(420, 360)

        layout = QVBoxLayout(self)
        intro = QLabel(
            (
                f"The model runs in the cloud. {PRODUCT_NAME} sends only the previewed "
                "structured summary; raw voltage and local paths stay on this computer."
            )
            if language == "en_US"
            else (
                f"模型在云端运行。{PRODUCT_NAME} 只发送可预览的结构化摘要；"
                "原始电压和本地路径始终留在当前电脑。"
            )
        )
        intro.setWordWrap(True)
        intro.setObjectName("Muted")
        layout.addWidget(intro)

        harness_row = QHBoxLayout()
        self.import_harness_button = QPushButton(
            "Import installed DeepSeek Harness"
            if language == "en_US"
            else "读取本机 DeepSeek Harness 配置"
        )
        self.import_harness_button.clicked.connect(self._import_harness)
        harness_row.addWidget(self.import_harness_button)
        harness_row.addStretch()
        layout.addLayout(harness_row)
        self.harness_status = QLabel()
        self.harness_status.setWordWrap(True)
        self.harness_status.setObjectName("Muted")
        layout.addWidget(self.harness_status)

        form = QFormLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItem(
            "Manual · AI off" if language == "en_US" else "手动 · 关闭 AI",
            AIMode.MANUAL.value,
        )
        self.mode_combo.addItem(
            (
                "Assistant · advice only"
                if language == "en_US"
                else "助手 · 仅解释与建议"
            ),
            AIMode.ASSISTANT.value,
        )
        self.mode_combo.addItem(
            (
                "Collaborative · confirmed tools"
                if language == "en_US"
                else "协作 · 确认后调用工具"
            ),
            AIMode.COLLABORATIVE.value,
        )
        self.mode_combo.setCurrentIndex(
            max(self.mode_combo.findData(settings.mode), 0)
        )
        form.addRow("AI mode" if language == "en_US" else "AI 模式", self.mode_combo)

        self.provider_combo = QComboBox()
        for key, profile in PROVIDER_PROFILES.items():
            self.provider_combo.addItem(profile["label"], key)
        self.provider_combo.setCurrentIndex(
            max(self.provider_combo.findData(settings.provider), 0)
        )
        self.provider_combo.currentIndexChanged.connect(
            self._provider_changed
        )
        form.addRow(
            "Provider" if language == "en_US" else "服务方式",
            self.provider_combo,
        )

        self.base_url_edit = QLineEdit(settings.base_url)
        self.base_url_edit.setPlaceholderText("https://api.deepseek.com")
        form.addRow(
            "API base URL" if language == "en_US" else "API 地址",
            self.base_url_edit,
        )

        self.model_edit = QComboBox()
        self.model_edit.setEditable(True)
        for model in PROVIDER_PROFILES.get(settings.provider, {}).get(
            "models",
            [],
        ):
            self.model_edit.addItem(model)
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
            "DEEPSEEK_API_KEY"
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
        self.api_key_env_edit = QLineEdit(settings.api_key_env)
        self.api_key_env_edit.setPlaceholderText(
            "CDSC_API_KEY / NEUROEPHYS_AI_API_KEY"
        )
        form.addRow(
            "Key environment variable"
            if language == "en_US"
            else "密钥环境变量",
            self.api_key_env_edit,
        )
        self.private_http_check = QCheckBox(
            (
                "Allow plain HTTP only for this private-network harness"
                if language == "en_US"
                else "仅对此机构内网 harness 允许 HTTP"
            )
        )
        self.private_http_check.setChecked(
            settings.allow_insecure_private_network
        )
        self.private_http_check.setToolTip(
            (
                "HTTP does not encrypt the key or request in transit. Enable only "
                "for a trusted institute private-network endpoint."
                if language == "en_US"
                else (
                    "HTTP 不会加密传输中的密钥与请求；只能对可信的机构内网地址启用。"
                )
            )
        )
        form.addRow(
            "Private network" if language == "en_US" else "机构内网",
            self.private_http_check,
        )
        self.persist_key_check = QCheckBox(
            (
                "Store in the operating-system credential vault"
                if language == "en_US"
                else "保存到操作系统凭据库"
            )
        )
        self.persist_key_check.setChecked(True)
        form.addRow(
            "Credential storage" if language == "en_US" else "密钥存储",
            self.persist_key_check,
        )
        self.stream_check = QCheckBox(
            "Stream the response" if language == "en_US" else "流式显示回复"
        )
        self.stream_check.setChecked(settings.stream)
        form.addRow(
            "Response" if language == "en_US" else "回复方式",
            self.stream_check,
        )
        self.retry_combo = QComboBox()
        for value in range(4):
            self.retry_combo.addItem(str(value), value)
        self.retry_combo.setCurrentIndex(
            max(self.retry_combo.findData(settings.retry_count), 0)
        )
        form.addRow(
            "Transient retries" if language == "en_US" else "临时错误重试",
            self.retry_combo,
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
        settings_content = QWidget()
        settings_content_layout = QVBoxLayout(settings_content)
        settings_content_layout.setContentsMargins(0, 0, 0, 0)
        settings_content_layout.addLayout(form)

        self.key_note = QLabel(
            (
                "The API key is never written to a project, log or exported report. "
                "It can be kept for this session, read from the provider environment "
                "variable, or saved in the operating-system credential vault."
            )
            if language == "en_US"
            else (
                "API 密钥不会写入项目、日志或导出报告。可仅在当前会话保存、"
                "通过 Provider 对应的环境变量提供，或保存到操作系统凭据库。"
            )
        )
        self.key_note.setWordWrap(True)
        self.key_note.setObjectName("Muted")
        settings_content_layout.addWidget(self.key_note)

        self.recommendation = QLabel(
            (
                "Recommended first configuration: DeepSeek API with "
                "deepseek-v4-flash. A laboratory service, Ollama or another compatible "
                "endpoint can use an OpenAI-compatible profile."
            )
            if language == "en_US"
            else (
                "建议第一阶段使用 DeepSeek API 与 deepseek-v4-flash。实验室私有"
                "服务、Ollama 或其他兼容服务可使用 OpenAI-compatible 配置。"
            )
        )
        self.recommendation.setWordWrap(True)
        self.recommendation.setObjectName("InsetPanel")
        self.recommendation.setContentsMargins(12, 9, 12, 9)
        settings_content_layout.addWidget(self.recommendation)

        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFrameShape(QFrame.NoFrame)
        settings_scroll.setWidget(settings_content)
        layout.addWidget(settings_scroll, 1)

        button_row = QHBoxLayout()
        self.health_button = QPushButton(
            "Check service" if language == "en_US" else "检测服务状态"
        )
        self.health_button.clicked.connect(self._check_health)
        button_row.addWidget(self.health_button)
        button_row.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.button(QDialogButtonBox.Save).setText(
            "Apply settings" if language == "en_US" else "应用设置"
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        button_row.addWidget(buttons)
        layout.addLayout(button_row)
        self._refresh_harness_status()
        self._provider_changed()

    def _refresh_harness_status(self) -> None:
        profiles = discover_deepseek_harness_profiles()
        if not profiles:
            self.harness_status.setText(
                (
                    "No supported local DeepSeek Harness configuration was found."
                    if self.language == "en_US"
                    else "未检测到受支持的本机 DeepSeek Harness 配置。"
                )
            )
            self.import_harness_button.setEnabled(False)
            return
        profile = profiles[0]
        self.import_harness_button.setEnabled(True)
        self.harness_status.setText(
            (
                f"Detected {profile.display_name}: {profile.default_model or 'model not set'} · "
                "endpoint metadata can be imported; the secret is not read."
                if self.language == "en_US"
                else (
                    f"已检测到 {profile.display_name}："
                    f"{profile.default_model or '未设置模型'}。可读取连接信息，"
                    "但不会读取 harness 的密钥文件。"
                )
            )
        )

    def _import_harness(self) -> None:
        profiles = discover_deepseek_harness_profiles()
        if not profiles:
            self._refresh_harness_status()
            return
        profile = profiles[0]
        index = self.provider_combo.findData("harness_sdk")
        self.provider_combo.blockSignals(True)
        self.provider_combo.setCurrentIndex(max(index, 0))
        self.provider_combo.blockSignals(False)
        self._provider_changed()
        self.base_url_edit.setText("harness://local")
        self.model_edit.clear()
        self.model_edit.addItems(list(profile.models))
        self.model_edit.setCurrentText(profile.default_model)
        self.api_key_env_edit.clear()
        self.api_key_edit.clear()
        self.private_http_check.setChecked(False)
        self.settings.harness_provider = profile.provider_id
        self.settings.managed_harness_name = profile.display_name
        self.recommendation.setText(
            (
                "Imported from the installed harness. Use Check service before "
                "saving. The App sends its own constrained project summary and does "
                "not copy the harness conversation."
                if self.language == "en_US"
                else (
                    "已选择本机 Harness SDK。模型和密钥由 Harness 管理，首次提问验证服务。"
                    "AI 可查询当前项目数据和结果；分析操作需在 app 内确认。"
                )
            )
        )
        self._refresh_harness_status()

    def _provider_changed(self) -> None:
        provider = str(self.provider_combo.currentData())
        profile = PROVIDER_PROFILES.get(provider, {})
        current_base = self.base_url_edit.text().strip()
        known_bases = {
            item["base_url"] for item in PROVIDER_PROFILES.values()
        }
        if not current_base or current_base in known_bases:
            self.base_url_edit.setText(str(profile.get("base_url", "")))
        models = list(profile.get("models", []))
        if models:
            self.model_edit.clear()
            self.model_edit.addItems(models)
            self.model_edit.setCurrentIndex(0)
        sdk = provider == "harness_sdk"
        stored = "" if sdk else get_api_key(provider)
        self.api_key_edit.setText(stored)
        local = bool(profile.get("local")) or sdk
        self.base_url_edit.setEnabled(not sdk)
        self.api_key_edit.setEnabled(not local)
        self.show_key.setEnabled(not local)
        self.persist_key_check.setEnabled(not local)
        self.api_key_env_edit.setEnabled(not local)
        self.private_http_check.setEnabled(provider == "institute_harness")
        self.api_key_edit.setPlaceholderText(
            (
                "No key required for local Ollama"
                if self.language == "en_US"
                else "本机 Ollama 不需要密钥"
            )
            if local
            else (
                "Provider API key"
                if self.language == "en_US"
                else "粘贴 Provider API 密钥"
            )
        )
        if sdk:
            profiles = discover_deepseek_harness_profiles()
            if profiles:
                chosen = next((p for p in profiles if p.provider_id == self.settings.harness_provider), profiles[0])
                self.settings.harness_provider = chosen.provider_id
                self.model_edit.clear()
                self.model_edit.addItems(list(chosen.models))
                self.model_edit.setCurrentText(self.settings.model if self.settings.model in chosen.models else chosen.default_model)
            self.key_note.setText("模型和凭据由本机 Harness 管理；无需复制密钥。" if self.language != "en_US" else "The installed Harness owns models and credentials. No key is copied.")
        elif local:
            self.key_note.setText(
                (
                    "Ollama runs on this computer. Project summaries stay local, "
                    "and no API key is required."
                    if self.language == "en_US"
                    else "Ollama 在当前电脑运行；项目摘要留在本机，也不需要 API 密钥。"
                )
            )
            self.recommendation.setText(
                (
                    "Start Ollama first, pull a tool-capable model, then use Check "
                    "service to list the installed models."
                    if self.language == "en_US"
                    else (
                        "请先启动 Ollama 并下载支持工具调用的模型，再点击“检测服务状态”"
                        "确认本机模型列表。"
                    )
                )
            )
        elif provider == "institute_harness":
            self.key_note.setText(
                (
                    "Use the institute key or its environment-variable name. The "
                    "App never copies the DeepSeek Harness credential file."
                    if self.language == "en_US"
                    else (
                        "请使用机构密钥或对应的环境变量名称。App 不会复制或读取 "
                        "DeepSeek Harness 的凭据文件。"
                    )
                )
            )
            self.recommendation.setText(
                (
                    "Use Import installed DeepSeek Harness to fill the endpoint and "
                    "model, then check the service."
                    if self.language == "en_US"
                    else (
                        "点击“读取本机 DeepSeek Harness 配置”自动填写地址与模型，"
                        "然后检测服务状态。"
                    )
                )
            )
        else:
            self.key_note.setText(
                (
                    "The API key is never written to a project, log or exported report. "
                    "It can be kept for this session, read from an environment variable, "
                    "or saved in the operating-system credential vault."
                    if self.language == "en_US"
                    else (
                        "API 密钥不会写入项目、日志或导出报告。可仅在当前会话保存、"
                        "通过环境变量提供，或保存到操作系统凭据库。"
                    )
                )
            )
            self.recommendation.setText(
                (
                    "Recommended online configuration: DeepSeek API with "
                    "deepseek-v4-flash. Laboratory services can use an "
                    "OpenAI-compatible profile."
                    if self.language == "en_US"
                    else (
                        "在线模式建议使用 DeepSeek API 与 deepseek-v4-flash；"
                        "实验室私有服务可使用 OpenAI-compatible 配置。"
                    )
                )
            )

    def _candidate_settings(self) -> AISettings:
        return AISettings(
            provider=str(self.provider_combo.currentData()),
            base_url=self.base_url_edit.text().strip(),
            model=self.model_edit.currentText().strip(),
            mode=str(self.mode_combo.currentData()),
            reasoning_effort=str(self.reasoning_combo.currentData()),
            timeout_seconds=self.settings.timeout_seconds,
            retry_count=int(self.retry_combo.currentData()),
            stream=self.stream_check.isChecked(),
            include_recent_log=self.include_log_check.isChecked(),
            selected_context_fields=list(self.settings.selected_context_fields),
            safety_identifier=self.settings.safety_identifier,
            api_key_env=self.api_key_env_edit.text().strip(),
            allow_insecure_private_network=(
                self.private_http_check.isChecked()
            ),
            managed_harness_name=self.settings.managed_harness_name,
            harness_provider=self.settings.harness_provider,
            api_key=self.api_key_edit.text().strip(),
        )

    def _check_health(self) -> None:
        result = check_provider_health(self._candidate_settings())
        QMessageBox.information(
            self,
            "Provider status" if self.language == "en_US" else "Provider 状态",
            (
                f"{result.get('message', '')}\n"
                f"Latency: {result.get('latency_ms', '—')} ms"
            ),
        )

    def _accept(self) -> None:
        candidate = self._candidate_settings()
        self.settings = candidate
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
        try:
            if self.settings.provider != "harness_sdk":
                store_api_key(
                    self.settings.provider,
                    self.settings.api_key,
                    persist_in_os_store=self.persist_key_check.isChecked(),
                )
        except RuntimeError as exc:
            QMessageBox.warning(
                self,
                (
                    "Credential vault unavailable"
                    if self.language == "en_US"
                    else "操作系统凭据库不可用"
                ),
                str(exc),
            )
        save_ai_preferences(self.settings)
        self.accept()


class ContextPreviewDialog(QDialog):
    def __init__(
        self,
        summary: dict[str, Any],
        language: str,
        selected_fields: list[str] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(
            "Cloud data preview"
            if language == "en_US"
            else "云端发送内容预览"
        )
        self.summary = summary
        self.language = language
        self.checks: dict[str, QCheckBox] = {}
        self.resize(1000, 680)
        self.setMinimumSize(420, 360)
        layout = QVBoxLayout(self)
        explanation = QLabel(
            (
                "These fields accompany questions in this project. Queryable data also permits "
                "on-demand reading of project results and saved conversation. Your question and "
                "recent conversation are included separately. Review once; change this selection any time."
            )
            if language == "en_US"
            else (
                "这是本项目对话可读取的上下文。“按需查询项目数据”还允许查询数据、结果和历史对话。"
                "问题与近期对话另行附加；本次打开项目确认一次即可，之后可随时调整。"
            )
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        body = QHBoxLayout()
        self.body_layout = body
        fields = QFrame()
        fields_layout = QVBoxLayout(fields)
        field_title = QLabel(
            "Fields included in the request"
            if language == "en_US"
            else "本次请求包含的字段"
        )
        field_title.setStyleSheet("font-weight: 700;")
        fields_layout.addWidget(field_title)
        explicit = set(selected_fields or [])
        for key in sorted(summary):
            if key == "local_only":
                continue
            box = QCheckBox(("按需查询项目数据、结果与历史对话" if language != "en_US" else
                            "On-demand project data, results and conversation") if key == "queryable_data" else key)
            box.setChecked(not explicit or key in explicit)
            box.toggled.connect(self._refresh_preview)
            self.checks[key] = box
            fields_layout.addWidget(box)
        fields_layout.addStretch()
        fields_scroll = QScrollArea()
        fields_scroll.setWidgetResizable(True)
        fields_scroll.setFrameShape(QFrame.NoFrame)
        fields_scroll.setWidget(fields)
        body.addWidget(fields_scroll, 1)
        self.viewer = QPlainTextEdit()
        self.viewer.setReadOnly(True)
        body.addWidget(self.viewer, 3)
        layout.addLayout(body, 1)
        self._refresh_preview()
        buttons = QDialogButtonBox(
            QDialogButtonBox.Cancel | QDialogButtonBox.Save
        )
        buttons.button(QDialogButtonBox.Save).setText(
            "Use selected fields"
            if language == "en_US"
            else "使用所选字段"
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self.body_layout.setDirection(
            QBoxLayout.TopToBottom
            if self.width() < 760
            else QBoxLayout.LeftToRight
        )

    def selected_fields(self) -> list[str]:
        return [key for key, box in self.checks.items() if box.isChecked()]

    def _refresh_preview(self) -> None:
        selected = {
            key: self.summary[key]
            for key in self.selected_fields()
            if key in self.summary
        }
        self.viewer.setPlainText(
            json.dumps(selected, ensure_ascii=False, indent=2)
        )


class AIAssistantDialog(QDialog):
    thread_changed = Signal(str)

    def __init__(
        self,
        *,
        state_getter: Callable[[], ProjectState | None],
        stage_getter: Callable[[], str],
        language_getter: Callable[[], str],
        response_handler: Callable[[AIResponse, str, str, str, str], None],
        plan_handler: Callable[[list[dict[str, Any]], str], None],
        tool_handler: Callable[[dict[str, Any]], None] | None = None,
        manual_handler: Callable[[], None],
        figure_capture_getter: Callable[[], tuple[bytes, str]] | None = None,
        general_conversation_path: Path | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.state_getter = state_getter
        self.stage_getter = stage_getter
        self.language_getter = language_getter
        self.response_handler = response_handler
        self.plan_handler = plan_handler
        self.tool_handler = tool_handler
        self.manual_handler = manual_handler
        self.figure_capture_getter = figure_capture_getter
        self.general_conversation_path = general_conversation_path
        self.settings = load_ai_settings()
        self.history: list[dict[str, str]] = []
        self.current_plan: list[dict[str, Any]] = []
        self.current_next_stage = "import"
        self.worker: AIWorker | None = None
        self.loaded_project_token = ""
        self.current_tool_calls: list[dict[str, Any]] = []
        self.stream_buffer = ""
        self.context_authorized = False
        self.request_project = None
        self.reading_mode = load_ai_reading_mode()
        self.response_details: dict[str, dict[str, Any]] = {}
        self.response_detail_counter = 0
        self.ephemeral_metadata: dict[str, Any] = (
            load_general_conversations(general_conversation_path)
            if general_conversation_path is not None
            else {"ai_history": [], "ai_threads": []}
        )
        self.current_thread_id = ""
        self.current_stage = ""
        self.stage_drafts: dict[str, str] = {}
        self.pending_image_png: bytes | None = None
        self.pending_image_label = ""

        self.resize(1280, 790)
        self.setMinimumSize(520, 420)
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
        self._cancel_request()
        self.context_authorized = False
        self.current_tool_calls = []
        self.current_plan = []
        self.loaded_project_token = project_token
        self.pending_image_png = None
        self.pending_image_label = ""
        self._update_attachment_label()
        metadata = self._thread_metadata()
        threads = ensure_threads(metadata)
        if self.state_getter() is None and len(threads) == 1 and not metadata["ai_history"]:
            set_thread_group(metadata, str(threads[0]["id"]), "general")
        if self.state_getter() is not None:
            self.current_stage = ""
            self.set_stage(self.stage_getter())
            return
        preferred = str(metadata.get("ai_active_thread_id", ""))
        self.current_thread_id = preferred if preferred in {str(row["id"]) for row in threads} else str(threads[-1]["id"])
        self._refresh_thread_list()
        self.activate_thread(self.current_thread_id)

    def set_stage(self, stage: str) -> None:
        """Keep one independently persisted conversation space per project stage."""
        if self.state_getter() is None or stage == self.current_stage:
            return
        if self.worker and self.worker.isRunning():
            return
        if self.current_stage:
            self.stage_drafts[self.current_stage] = self.question_edit.toPlainText()
        self.current_stage = stage
        self.question_edit.setPlainText(self.stage_drafts.get(stage, ""))
        metadata = self._thread_metadata()
        title = STAGE_LABELS[self.language_getter()].get(stage, stage)
        thread_id = ensure_stage_thread(metadata, stage, title)
        self._refresh_thread_list()
        self.activate_thread(thread_id)

    def _thread_metadata(self) -> dict[str, Any]:
        state = self.state_getter()
        return state.metadata if state is not None else self.ephemeral_metadata

    def _persist_threads(self) -> None:
        state = self.state_getter()
        if state is not None:
            from .project import save_ai_conversation
            save_ai_conversation(state)
        elif self.general_conversation_path is not None:
            save_general_conversations(self.general_conversation_path, self.ephemeral_metadata)

    def _refresh_thread_list(self) -> None:
        metadata = self._thread_metadata()
        current = self.current_thread_id
        query = self.thread_search.text().strip()
        stage = None if (self.state_getter() is None or self.all_steps_checkbox.isChecked()
                            or query) else self.current_stage
        rows = matching_threads(metadata, query, stage=stage)
        self.thread_combo.blockSignals(True)
        self.thread_combo.clear()
        for row in rows:
            thread_id = str(row["id"])
            count = len(thread_records(metadata, thread_id))
            group = group_label(str(row.get("group", "project")), self.language_getter())
            self.thread_combo.addItem(f"{group} / {row['title']}  ·  {count}", thread_id)
        index = self.thread_combo.findData(current)
        if index >= 0:
            self.thread_combo.setCurrentIndex(index)
        self.thread_combo.blockSignals(False)

    def activate_thread(self, thread_id: str) -> None:
        if self.worker and self.worker.isRunning():
            return
        metadata = self._thread_metadata()
        if thread_id not in {str(row["id"]) for row in ensure_threads(metadata)}:
            return
        self.current_thread_id = thread_id
        metadata["ai_active_thread_id"] = thread_id
        stage = str(next((row.get("stage", "") for row in ensure_threads(metadata)
                          if row.get("id") == thread_id), ""))
        if stage:
            metadata.setdefault("ai_active_thread_by_stage", {})[stage] = thread_id
        self._persist_threads()
        row = next(row for row in ensure_threads(metadata) if row["id"] == thread_id)
        self.thread_group_combo.blockSignals(True)
        self.thread_group_combo.setCurrentIndex(
            max(self.thread_group_combo.findData(row.get("group", "project")), 0)
        )
        self.thread_group_combo.blockSignals(False)
        self.history = []
        self.response_details = {}
        self.response_detail_counter = 0
        self.conversation.clear()
        for record in thread_records(metadata, thread_id)[-40:]:
            question = str(record.get("question", "")).strip()
            answer = str(record.get("answer", "")).strip()
            if question:
                self.history.append({"role": "user", "content": question})
                self._append_message("user", question, record=record)
            if answer:
                self.history.append({"role": "assistant", "content": answer})
                self._append_message("assistant", answer, record=record)
        self.history = self.history[-40:]
        self._refresh_thread_list()
        self.thread_changed.emit(thread_id)

    def _new_thread(self) -> None:
        metadata = self._thread_metadata()
        group = "general" if self.state_getter() is None else "project"
        thread_id = create_thread(metadata, group=group,
                                  stage=self.current_stage if self.state_getter() else "")
        self._persist_threads()
        self.thread_search.clear()
        self._refresh_thread_list()
        self.activate_thread(thread_id)

    def _rename_thread(self) -> None:
        metadata = self._thread_metadata()
        row = next((row for row in ensure_threads(metadata)
                    if row["id"] == self.current_thread_id), None)
        if row is None:
            return
        title, accepted = QInputDialog.getText(
            self, "Rename conversation" if self.language_getter() == "en_US" else "重命名对话",
            "Title" if self.language_getter() == "en_US" else "对话名称",
            text=str(row.get("title", "")),
        )
        if accepted and rename_thread(metadata, self.current_thread_id, title):
            self._persist_threads()
            self._refresh_thread_list()
            self.thread_changed.emit(self.current_thread_id)

    def _change_thread_group(self) -> None:
        group = str(self.thread_group_combo.currentData() or "")
        if set_thread_group(self._thread_metadata(), self.current_thread_id, group):
            self._persist_threads()
            self._refresh_thread_list()
            self.thread_changed.emit(self.current_thread_id)

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
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Manual", AIMode.MANUAL.value)
        self.mode_combo.addItem("Assistant", AIMode.ASSISTANT.value)
        self.mode_combo.addItem("Collaborative", AIMode.COLLABORATIVE.value)
        self.mode_combo.setCurrentIndex(
            max(self.mode_combo.findData(self.settings.mode), 0)
        )
        self.mode_combo.currentIndexChanged.connect(self._mode_changed)
        header.addWidget(self.mode_combo)
        self.context_button = QPushButton()
        self.context_button.clicked.connect(self._show_context)
        self.manual_button = QPushButton()
        self.manual_button.clicked.connect(self.manual_handler)
        self.settings_button = QPushButton()
        self.settings_button.clicked.connect(self._open_settings)
        root.addLayout(header)
        actions = QHBoxLayout()
        actions.addWidget(self.context_button)
        actions.addWidget(self.manual_button)
        actions.addWidget(self.settings_button)
        actions.addStretch()
        root.addLayout(actions)

        self.status_frame = QFrame()
        self.status_frame.setObjectName("InsetPanel")
        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(12, 8, 12, 8)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label, 1)
        root.addWidget(self.status_frame)

        thread_row = QHBoxLayout()
        self.thread_search = QLineEdit()
        self.thread_search.setClearButtonEnabled(True)
        self.thread_search.textChanged.connect(self._refresh_thread_list)
        self.thread_search.setMinimumWidth(110)
        thread_row.addWidget(self.thread_search, 2)
        self.thread_combo = QComboBox()
        self.thread_combo.setMinimumWidth(150)
        self.thread_combo.currentIndexChanged.connect(
            lambda: self.activate_thread(str(self.thread_combo.currentData() or ""))
        )
        thread_row.addWidget(self.thread_combo, 3)
        self.new_thread_button = QPushButton()
        self.new_thread_button.clicked.connect(self._new_thread)
        thread_row.addWidget(self.new_thread_button)
        self.rename_thread_button = QPushButton()
        self.rename_thread_button.clicked.connect(self._rename_thread)
        thread_row.addWidget(self.rename_thread_button)
        root.addLayout(thread_row)
        self.all_steps_checkbox = QCheckBox()
        self.all_steps_checkbox.toggled.connect(self._refresh_thread_list)
        root.addWidget(self.all_steps_checkbox)
        group_row = QHBoxLayout()
        self.thread_group_label = QLabel()
        group_row.addWidget(self.thread_group_label)
        self.thread_group_combo = QComboBox()
        self.thread_group_combo.currentIndexChanged.connect(self._change_thread_group)
        group_row.addWidget(self.thread_group_combo, 1)
        root.addLayout(group_row)

        body = QHBoxLayout()
        self.body_layout = body
        body.setSpacing(12)

        chat_frame = QFrame()
        chat_frame.setObjectName("Card")
        chat_layout = QVBoxLayout(chat_frame)
        chat_layout.setContentsMargins(12, 12, 12, 12)
        quick_header = QHBoxLayout()
        self.quick_title = QLabel()
        self.quick_title.setStyleSheet("font-weight: 700;")
        quick_header.addWidget(self.quick_title)
        quick_header.addStretch()
        self.reading_label = QLabel()
        self.reading_label.setObjectName("Muted")
        quick_header.addWidget(self.reading_label)
        self.reading_combo = QComboBox()
        self.reading_combo.addItem("简洁", "compact")
        self.reading_combo.addItem("完整", "full")
        self.reading_combo.setCurrentIndex(
            max(self.reading_combo.findData(self.reading_mode), 0)
        )
        self.reading_combo.currentIndexChanged.connect(self._reading_mode_changed)
        quick_header.addWidget(self.reading_combo)
        chat_layout.addLayout(quick_header)
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

        self.conversation = BubbleChatView()
        self.conversation.anchorClicked.connect(self._open_response_detail)
        chat_layout.addWidget(self.conversation, 1)

        self.question_edit = ChatComposer()
        self.question_edit.setMaximumHeight(105)
        self.question_edit.submitted.connect(lambda: self._submit("ask"))
        chat_layout.addWidget(self.question_edit)
        attachment_row = QHBoxLayout()
        self.attach_chart_button = QPushButton()
        self.attach_chart_button.clicked.connect(self.attach_current_chart)
        attachment_row.addWidget(self.attach_chart_button)
        self.attachment_label = QLabel()
        self.attachment_label.setObjectName("Muted")
        self.attachment_label.setWordWrap(True)
        attachment_row.addWidget(self.attachment_label, 1)
        self.remove_attachment_button = QPushButton()
        self.remove_attachment_button.clicked.connect(self._remove_attachment)
        attachment_row.addWidget(self.remove_attachment_button)
        chat_layout.addLayout(attachment_row)
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
        self.cancel_button = QPushButton()
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self._cancel_request)
        send_row.addWidget(self.cancel_button)
        chat_layout.addLayout(send_row)
        body.addWidget(chat_frame, 3)

        plan_frame = QFrame()
        plan_frame.setObjectName("Card")
        # Keep both work areas usable without forcing a desktop-sized dialog.
        # Layout stretch factors shrink the plan alongside chat on small screens.
        plan_frame.setMinimumWidth(250)
        self.plan_frame = plan_frame
        plan_layout = QVBoxLayout(plan_frame)
        plan_layout.setContentsMargins(12, 12, 12, 12)
        self.plan_title = QLabel()
        self.plan_title.setStyleSheet("font-weight: 700;")
        plan_layout.addWidget(self.plan_title)
        self.plan_explanation = QLabel()
        self.plan_explanation.setWordWrap(True)
        self.plan_explanation.setObjectName("Muted")
        plan_layout.addWidget(self.plan_explanation)
        self.plan_table = QTableWidget(0, 5)
        self.plan_table.verticalHeader().setVisible(False)
        self.plan_table.setEditTriggers(
            QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed
        )
        self.plan_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.plan_table.setWordWrap(True)
        plan_header = self.plan_table.horizontalHeader()
        plan_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        plan_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        plan_header.setSectionResizeMode(2, QHeaderView.Stretch)
        plan_header.setSectionResizeMode(3, QHeaderView.Stretch)
        plan_header.setSectionResizeMode(4, QHeaderView.Stretch)
        plan_layout.addWidget(self.plan_table, 1)
        self.tool_frame = QFrame()
        self.tool_frame.setObjectName("InsetPanel")
        tool_layout = QVBoxLayout(self.tool_frame)
        self.tool_title = QLabel()
        self.tool_title.setStyleSheet("font-weight: 700;")
        tool_layout.addWidget(self.tool_title)
        self.tool_summary = QLabel()
        self.tool_summary.setWordWrap(True)
        tool_layout.addWidget(self.tool_summary)
        self.review_tool_button = QPushButton()
        self.review_tool_button.clicked.connect(self._review_first_tool)
        tool_layout.addWidget(self.review_tool_button)
        self.tool_frame.setVisible(False)
        plan_layout.addWidget(self.tool_frame)
        self.apply_plan_button = QPushButton()
        self.apply_plan_button.setEnabled(False)
        self.apply_plan_button.clicked.connect(self._apply_plan)
        plan_layout.addWidget(self.apply_plan_button)
        body.addWidget(plan_frame, 2)
        plan_frame.setVisible(False)
        root.addLayout(body, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.hide)
        root.addWidget(buttons)
        self.close_buttons = buttons

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        compact = self.width() < 900
        self.body_layout.setDirection(
            QBoxLayout.TopToBottom
            if compact
            else QBoxLayout.LeftToRight
        )
        self.plan_frame.setMinimumWidth(0 if compact else 250)

    def set_language(self, language: str) -> None:
        english = language == "en_US"
        self.setWindowTitle(
            f"{PRODUCT_NAME} assistant" if english else f"{PRODUCT_NAME} 助手"
        )
        self.title_label.setText(
            f"{PRODUCT_NAME} assistant" if english else f"{PRODUCT_NAME} 助手"
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
        self.thread_search.setPlaceholderText(
            "Search titles and messages" if english else "搜索对话名称与内容"
        )
        self.new_thread_button.setText("New chat" if english else "新对话")
        self.rename_thread_button.setText("Rename" if english else "重命名")
        self.thread_group_label.setText("Group" if english else "对话分组")
        self.all_steps_checkbox.setText("Search all steps and older chats" if english else "跨步骤查找及查看旧对话")
        current_group = self.thread_group_combo.currentData()
        self.thread_group_combo.blockSignals(True)
        self.thread_group_combo.clear()
        for group in THREAD_GROUPS:
            self.thread_group_combo.addItem(group_label(group, self.language_getter()), group)
        self.thread_group_combo.setCurrentIndex(max(self.thread_group_combo.findData(current_group), 0))
        self.thread_group_combo.blockSignals(False)
        if self.current_thread_id:
            self._refresh_thread_list()
        self.quick_title.setText(
            "Start from a defined task" if english else "从明确任务开始"
        )
        self.reading_label.setText("View" if english else "阅读")
        self.reading_combo.setItemText(0, "Concise" if english else "简洁")
        self.reading_combo.setItemText(1, "Full" if english else "完整")
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
                "Ask about your data, a chart, methods, app use or another topic. "
                "Enter to send · Shift+Enter for a new line."
            )
            if english
            else (
                "可询问数据、图、科研方法、软件操作或其他问题。"
                "回车发送，Shift+回车换行。"
            )
        )
        self.attach_chart_button.setText("Interpret current chart" if english else "解读当前图")
        self.remove_attachment_button.setText("Remove" if english else "移除")
        self._update_attachment_label()
        self.privacy_label.setText(
            (
                "No raw numeric signal or local path is sent. A chart image is sent only "
                "after preview and approval; analysis still needs confirmation."
            )
            if english
            else "不发送原始数值或本地路径；图像仅在预览确认后发送，分析仍需确认。"
        )
        self.send_button.setText("Ask AI" if english else "询问 AI")
        self.cancel_button.setText("Cancel" if english else "取消请求")
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
            ["Use", "Stage", "Why", "Pre-\nrequisites", "Recommended\nparameters"]
            if english
            else ["采用", "阶段", "为什么做", "前提条件", "参数建议"]
        )
        self.apply_plan_button.setText(
            "Apply plan to project" if english else "将方案应用到项目"
        )
        self.tool_title.setText(
            "Proposed local action" if english else "建议的本地操作"
        )
        self.review_tool_button.setText(
            "Review and confirm" if english else "审核并确认"
        )
        self.close_buttons.button(QDialogButtonBox.Close).setText(
            "Close" if english else "关闭"
        )
        self._refresh_status()
        self._render_plan()

    def _update_attachment_label(self) -> None:
        attached = self.pending_image_png is not None
        english = self.language_getter() == "en_US"
        self.attachment_label.setText(
            (f"Attached: {self.pending_image_label}" if english else f"已附：{self.pending_image_label}")
            if attached else ("No chart attached" if english else "未附加图像")
        )
        self.remove_attachment_button.setVisible(attached)

    def _remove_attachment(self) -> None:
        self.pending_image_png = None
        self.pending_image_label = ""
        self._update_attachment_label()

    def attach_current_chart(self) -> bool:
        english = self.language_getter() == "en_US"
        if self.settings.provider not in {"harness_sdk", "openai_compatible", "openai_responses"}:
            QMessageBox.information(self, "AI",
                "This connection has no chart upload path. Choose Harness SDK, OpenAI-compatible Chat, or OpenAI Responses with a vision-capable model."
                if english else "当前连接未适配图像上传。请选择支持读图的 Harness SDK、OpenAI-compatible Chat 或 OpenAI Responses 模型。")
            return False
        if self.figure_capture_getter is None:
            return False
        try:
            image_png, label = self.figure_capture_getter()
        except (OSError, ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "AI", str(exc))
            return False
        if not confirm_chart_attachment(image_png, self.language_getter(), self,
                                        self.settings.provider_label):
            return False
        self.pending_image_png = image_png
        self.pending_image_label = label
        self._update_attachment_label()
        return True

    def _refresh_status(self) -> None:
        english = self.language_getter() == "en_US"
        mode_label = self.mode_combo.currentText()
        if self.settings.ai_mode == AIMode.MANUAL:
            self.status_label.setText(
                (
                    f"{mode_label} · no online request can be sent; all deterministic "
                    "analysis remains available."
                    if english
                    else (
                        f"{mode_label} · 当前不会发送在线请求；全部确定性分析功能仍可使用。"
                    )
                )
            )
            return
        if self.settings.configured:
            self.status_label.setText(
                (
                    f"{mode_label} · ready · {self.settings.provider_label} · "
                    f"{self.settings.model}"
                )
                if english
                else (
                    f"{mode_label} · 已就绪 · {self.settings.provider_label} · "
                    f"{self.settings.model}"
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
        summary = build_project_summary(
            self.state_getter(),
            self.stage_getter(),
            include_recent_log=self.settings.include_recent_log,
        )
        if self.settings.provider == "harness_sdk":
            summary["queryable_data"] = {
                "enabled": True,
                "description": "Allow on-demand pages of events, trials, spikes, Unit metrics, analysis results, logs and project conversation. No raw voltage or local paths.",
                "scope": "Current project only; snapshot refreshed for each question",
            }
        return summary

    def _show_context(self) -> None:
        dialog = ContextPreviewDialog(
            self._summary(),
            self.language_getter(),
            self.settings.selected_context_fields,
            self,
        )
        if dialog.exec() == QDialog.Accepted:
            self.settings.selected_context_fields = dialog.selected_fields()
            save_ai_preferences(self.settings)
            self.context_authorized = True

    def _mode_changed(self) -> None:
        self.settings.mode = str(self.mode_combo.currentData())
        save_ai_preferences(self.settings)
        self._refresh_status()
        enabled = self.settings.ai_mode != AIMode.MANUAL
        for button in (
            self.send_button,
            self.explain_button,
            self.review_button,
            self.plan_button,
            self.error_button,
        ):
            button.setEnabled(enabled)

    def _open_settings(self) -> None:
        dialog = AISettingsDialog(
            self.settings,
            self.language_getter(),
            self,
        )
        if dialog.exec() == QDialog.Accepted:
            self.settings = dialog.settings
            self.context_authorized = False
            self.mode_combo.blockSignals(True)
            self.mode_combo.setCurrentIndex(
                max(self.mode_combo.findData(self.settings.mode), 0)
            )
            self.mode_combo.blockSignals(False)
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
        if self.state_getter() is not None:
            selected = next((row for row in ensure_threads(self._thread_metadata())
                             if row.get("id") == self.current_thread_id), None)
            if selected is not None and selected.get("stage") != self.stage_getter():
                QMessageBox.information(
                    self,
                    "Select this workflow step" if self.language_getter() == "en_US" else "请先切换分析步骤",
                    ("This is a conversation from another step. Select that workflow step before continuing it."
                     if self.language_getter() == "en_US" else
                     "这是其他步骤的历史对话。请先切换到对应的分析步骤，再继续提问。"),
                )
                return
        if self.settings.ai_mode == AIMode.MANUAL:
            QMessageBox.information(
                self,
                "AI is off" if self.language_getter() == "en_US" else "AI 已关闭",
                (
                    "Switch to Assistant or Collaborative mode to send an online "
                    "request."
                    if self.language_getter() == "en_US"
                    else "切换到助手或协作模式后才能发送在线请求。"
                ),
            )
            return
        question = self.question_edit.toPlainText().strip()
        if not question and self.pending_image_png is not None:
            question = "Please interpret the attached chart." if self.language_getter() == "en_US" else "请解读附加的这张图。"
        if not question:
            return
        if not self.settings.configured:
            self._open_settings()
            if not self.settings.configured:
                return
        if not self.context_authorized:
            preview = ContextPreviewDialog(
                self._summary(), self.language_getter(), self.settings.selected_context_fields, self)
            if preview.exec() != QDialog.Accepted:
                return
            self.settings.selected_context_fields = preview.selected_fields()
            save_ai_preferences(self.settings)
            self.context_authorized = True
        language = self.language_getter()
        thread_id = self.current_thread_id
        image_png = self.pending_image_png
        image_label = self.pending_image_label if image_png is not None else ""
        shown_question = question + (f"\n📎 {image_label}" if image_label else "")
        self._append_message("user", shown_question)
        self.history.append({"role": "user", "content": question})
        self._set_running(True)
        self.request_project = self.state_getter()
        queries = (ProjectQueries(self.request_project, self.stage_getter(), self.settings.mode)
                   if self.settings.provider == "harness_sdk" else None)
        self.worker = AIWorker(
            self.settings,
            question=question,
            task=task,
            language=language,
            project_summary=self._summary(),
            history=self.history[:-1],
            project_queries=queries,
            image_png=image_png,
            parent=self,
        )
        self.worker.completed.connect(
            lambda response: self._on_completed(response, question, task, thread_id, image_label)
        )
        self.worker.failed.connect(self._on_failed)
        self.worker.streamed.connect(self._on_streamed)
        self.worker.start()

    def _on_streamed(self, text: str) -> None:
        self.stream_buffer += text
        self.status_label.setText(
            (
                f"Receiving a streamed response · {len(self.stream_buffer)} characters"
                if self.language_getter() == "en_US"
                else f"正在流式接收回复 · 已接收 {len(self.stream_buffer)} 个字符"
            )
        )

    def _cancel_request(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()

    def _set_running(self, running: bool) -> None:
        for button in (
            self.send_button,
            self.explain_button,
            self.review_button,
            self.plan_button,
            self.error_button,
            self.settings_button,
            self.mode_combo,
            self.thread_combo,
            self.thread_group_combo,
            self.new_thread_button,
            self.rename_thread_button,
            self.attach_chart_button,
        ):
            button.setEnabled(not running)
        self.cancel_button.setVisible(running)
        english = self.language_getter() == "en_US"
        if running:
            self.stream_buffer = ""
            self.status_label.setText(
                
                    f"Waiting for cloud AI; {PRODUCT_NAME} remains unchanged..."
                    if english
                    else f"正在等待云端 AI；{PRODUCT_NAME} 项目尚未发生任何修改……"
                
            )
        else:
            self._refresh_status()

    def _reading_mode_changed(self) -> None:
        self.reading_mode = str(self.reading_combo.currentData() or "compact")
        save_ai_reading_mode(self.reading_mode)
        if self.current_thread_id:
            self.activate_thread(self.current_thread_id)

    def _open_response_detail(self, url: QUrl) -> None:
        if url.scheme() != "neuroephys" or url.host() != "ai-detail":
            return
        key = url.path().strip("/")
        record = self.response_details.get(key)
        if record:
            AIResponseDetailDialog(record, self.language_getter(), self).exec()

    def _append_message(
        self,
        role: str,
        text: str,
        *,
        record: dict[str, Any] | None = None,
    ) -> None:
        english = self.language_getter() == "en_US"
        label = ("You" if english else "你") if role == "user" else "NeuroEphys AI"
        if role == "assistant" and self.reading_mode == "compact":
            detail_record = dict(record or {})
            detail_record.setdefault("answer", text)
            self.response_detail_counter += 1
            detail_key = str(self.response_detail_counter)
            self.response_details[detail_key] = detail_record
            view = build_readable_ai_view(
                text,
                warnings=list(detail_record.get("warnings", [])),
                suggested_next_stage=str(
                    detail_record.get("suggested_next_stage", "")
                ),
                tool_calls=list(detail_record.get("tool_calls", [])),
                query_evidence=list(detail_record.get("query_evidence", [])),
                language=self.language_getter(),
            )
            body = readable_view_html(
                view,
                detail_url=f"neuroephys://ai-detail/{detail_key}",
                language=self.language_getter(),
            )
        elif role == "assistant" and record:
            body = full_response_html(record, self.language_getter())
        else:
            body = escape(text).replace("\n", "<br>")
            if role == "user" and record and isinstance(record.get("chart_attachment"), dict):
                body += "<br>📎 " + escape(str(record["chart_attachment"].get("label", "chart")))
        self.conversation.append_message(role, label, body)
        scrollbar = self.conversation.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_completed(
        self,
        response: AIResponse,
        question: str,
        task: str,
        thread_id: str,
        image_label: str,
    ) -> None:
        self._set_running(False)
        if self.request_project is not self.state_getter():
            return
        self.history.append({"role": "assistant", "content": response.answer})
        self.history = self.history[-40:]
        response_record = response.audit_record(question, task)
        response_record["thread_id"] = thread_id
        if image_label and self.state_getter() is not None:
            metadata = self._thread_metadata()
            row = next((row for row in ensure_threads(metadata) if row["id"] == thread_id), None)
            if row and row.get("group") == "project" and not thread_records(metadata, thread_id):
                set_thread_group(metadata, thread_id, "figures")
            if row and row.get("automatic_title") and question in {
                "请解读附加的这张图。", "Please interpret the attached chart.",
            }:
                prefix = "Chart · " if self.language_getter() == "en_US" else "图表 · "
                rename_thread(metadata, thread_id, prefix + redact_sensitive_text(image_label))
        if image_label:
            response_record["chart_attachment"] = {
                "label": redact_sensitive_text(image_label), "mime_type": "image/png", "image_bytes_saved": False,
                "chart_pixels_sent_after_preview": True,
                "may_contain_raw_traces_or_labels": True,
            }
            response_record["raw_voltage_array_sent"] = False
            response_record["raw_voltage_sent"] = None  # Visible chart pixels can contain traces.
            response_record["local_paths_sent"] = None  # The approved image may contain text labels.
        if self.state_getter() is None:
            record_in_thread(self.ephemeral_metadata, response_record, thread_id)
            self._persist_threads()
        self._append_message(
            "assistant",
            response.answer,
            record=response_record,
        )
        self.current_plan = response.plan
        self.current_next_stage = response.suggested_next_stage
        self.current_tool_calls = response.tool_calls
        self._render_plan()
        self._render_tool_calls()
        self.plan_frame.setVisible(bool(self.current_plan or self.current_tool_calls))
        self.response_handler(response, question, task, thread_id, image_label)
        self.question_edit.clear()
        self._remove_attachment()
        row = next((row for row in ensure_threads(self._thread_metadata())
                    if row["id"] == thread_id), None)
        if row is not None:
            self.thread_group_combo.blockSignals(True)
            self.thread_group_combo.setCurrentIndex(
                max(self.thread_group_combo.findData(row.get("group", "project")), 0)
            )
            self.thread_group_combo.blockSignals(False)
        self._refresh_thread_list()
        self.thread_changed.emit(thread_id)
        if response.query_evidence:
            self.status_label.setText(
                f"已查询 {len(response.query_evidence)} 项项目证据；详情保存在项目对话记录。"
                if self.language_getter() != "en_US" else
                f"Read {len(response.query_evidence)} project evidence items; recorded with the conversation.")
        if self.state_getter() is not None and self.stage_getter() != self.current_stage:
            QTimer.singleShot(0, lambda: self.set_stage(self.stage_getter()))

    def _on_failed(self, details: str) -> None:
        self._set_running(False)
        if self.request_project is not self.state_getter():
            return
        self._append_message("assistant", "请求未完成 / Request incomplete: " + details)
        if self.state_getter() is not None and self.stage_getter() != self.current_stage:
            QTimer.singleShot(0, lambda: self.set_stage(self.stage_getter()))
        parent = self.parent()
        if parent is not None and hasattr(parent, "ai_sidebar_status"):
            parent.ai_sidebar_status.setText(details)
        english = self.language_getter() == "en_US"
        if self.settings.provider == "harness_sdk":
            QMessageBox.critical(self, "AI", details + (
                "\n\nNo analysis was changed. Check the installed Harness login, selected model, network and account quota. Do not copy its key into this app."
                if english else
                "\n\n没有修改分析。请检查本机 Harness 登录、所选模型、网络和账户额度，无需把 Harness 密钥复制到 App。"))
            return
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
            enabled = QTableWidgetItem()
            enabled.setFlags(
                Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable
            )
            enabled.setCheckState(Qt.Checked)
            self.plan_table.setItem(row, 0, enabled)
            values = (
                STAGE_LABELS[language].get(item["stage"], item["stage"]),
                item.get("reason", ""),
                "\n".join(item.get("prerequisites", [])),
                parameters,
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value or "—")
                cell.setToolTip(value)
                self.plan_table.setItem(row, column + 1, cell)
        self.plan_table.resizeRowsToContents()
        self.apply_plan_button.setEnabled(bool(self.current_plan))

    def _apply_plan(self) -> None:
        if not self.current_plan:
            return
        edited: list[dict[str, Any]] = []
        reverse_labels = {
            label: stage
            for stage, label in STAGE_LABELS[self.language_getter()].items()
        }
        for row, original in enumerate(self.current_plan):
            enabled = self.plan_table.item(row, 0)
            if enabled is None or enabled.checkState() != Qt.Checked:
                continue
            stage_text = self.plan_table.item(row, 1).text().strip()
            stage = reverse_labels.get(stage_text, stage_text)
            if stage not in STAGE_LABELS[self.language_getter()]:
                QMessageBox.warning(
                    self,
                    "Invalid workflow stage"
                    if self.language_getter() == "en_US"
                    else "工作流阶段无效",
                    stage_text,
                )
                return
            item = dict(original)
            item["stage"] = stage
            item["reason"] = self.plan_table.item(row, 2).text().strip()
            item["prerequisites"] = [
                line.strip()
                for line in self.plan_table.item(row, 3).text().splitlines()
                if line.strip()
            ]
            edited.append(item)
        self.plan_handler(edited, self.current_next_stage)

    def _render_tool_calls(self) -> None:
        if not self.current_tool_calls:
            self.tool_frame.setVisible(False)
            return
        state = self.state_getter()
        details = []
        for call in self.current_tool_calls:
            validation = validate_tool_call(
                call.get("name", ""),
                call.get("arguments", {}),
                state,
                self.settings.ai_mode,
            )
            status = "valid" if validation.valid else "blocked"
            details.append(
                f"{call.get('name')} · {status}\n"
                f"{json.dumps(call.get('arguments', {}), ensure_ascii=False)}"
            )
        self.tool_summary.setText("\n\n".join(details))
        self.tool_frame.setVisible(True)

    def _review_first_tool(self) -> None:
        if not self.current_tool_calls:
            return
        call = self.current_tool_calls[0]
        validation = validate_tool_call(
            call.get("name", ""),
            call.get("arguments", {}),
            self.state_getter(),
            self.settings.ai_mode,
        )
        english = self.language_getter() == "en_US"
        if not validation.valid:
            QMessageBox.warning(
                self,
                "Tool proposal blocked" if english else "工具建议已阻止",
                "\n".join(validation.errors),
            )
            return
        spec = validation.spec
        body = (
            f"Tool: {call['name']}\n"
            f"Stage: {spec.stage if spec else '—'}\n"
            f"Risk: {spec.risk if spec else '—'}\n"
            f"Arguments:\n{json.dumps(call.get('arguments', {}), ensure_ascii=False, indent=2)}\n\n"
            + "\n".join(validation.warnings)
        )
        accepted = QMessageBox.question(
            self,
            "Confirm local action" if english else "确认本地操作",
            body,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if accepted != QMessageBox.Yes:
            return
        if self.tool_handler:
            self.tool_handler(call)
