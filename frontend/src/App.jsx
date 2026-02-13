import React, { useEffect, useMemo, useState } from "react";
import Button from "./components/Button";

const apiBase = "/api";

// 时间格式化工具函数
const formatRelativeTime = (dateString) => {
  if (!dateString) return "";

  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);
  const diffWeeks = Math.floor(diffDays / 7);

  // 超过7天显示具体日期
  if (diffDays > 7) {
    return date.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
  }

  // 1周内显示相对时间
  if (diffDays > 0) {
    return `${diffDays}天前`;
  }
  if (diffHours > 0) {
    return `${diffHours}小时前`;
  }
  if (diffMinutes > 0) {
    return `${diffMinutes}分钟前`;
  }
  return "刚刚";
};

const formatFullTime = (dateString) => {
  if (!dateString) return "";
  const date = new Date(dateString);
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false
  });
};

const emptySettings = {
  fetch_interval: 300,
  target_lang: "zh",
  baidu_appid: "",
  baidu_secret: "",
  deepseek_api_key: "",
  deepseek_base_url: "https://api.deepseek.com",
  deepseek_model: "deepseek-chat"
};

export default function App() {
  const [theme, setTheme] = useState("light");
  const [view, setView] = useState("inbox");
  const [showWizard, setShowWizard] = useState(false);
  const [emails, setEmails] = useState([]);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [reply, setReply] = useState("");
  const [replyTranslation, setReplyTranslation] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState(null);
  const [isTranslating, setIsTranslating] = useState(false);
  const [isReverseTranslating, setIsReverseTranslating] = useState(false);  // 反向翻译中
  const [categories, setCategories] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [settings, setSettings] = useState(emptySettings);
  const [mailAccount, setMailAccount] = useState(null);
  const [processingStatus, setProcessingStatus] = useState({}); // { id: 'analyzing' | 'sending' | 'sent' | 'deleting' }
  const [processingSuccess, setProcessingSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // 当前时间，用于动态更新相对时间显示
  const [now, setNow] = useState(new Date());

  // 每分钟更新一次当前时间
  useEffect(() => {
    const timer = setInterval(() => {
      setNow(new Date());
    }, 60000); // 60秒更新一次
    return () => clearInterval(timer);
  }, []);

  // 分页状态
  const [emailPage, setEmailPage] = useState(1);
  const [emailPageSize, setEmailPageSize] = useState(10);
  const [emailTotal, setEmailTotal] = useState(0);
  const [emailTotalPages, setEmailTotalPages] = useState(0);
  const [emailTotalCount, setEmailTotalCount] = useState(0);  // 总邮件数
  const [emailPendingCount, setEmailPendingCount] = useState(0);  // 待处理数

  // Loading states for async actions
  const [isSyncing, setIsSyncing] = useState(false);
  const [isGeneratingAI, setIsGeneratingAI] = useState(false);
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [categoryOperation, setCategoryOperation] = useState({ type: null, id: null }); // type: 'save' | 'delete'
  const [templateOperation, setTemplateOperation] = useState({ type: null, id: null }); // type: 'save' | 'delete'

  // Check if first time setup is needed
  const needsSetup = useMemo(() => {
    // Only verify after loading is complete and we have data
    if (isLoading) return false;
    return !mailAccount?.email || !settings.deepseek_api_key;
  }, [mailAccount, settings, isLoading]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      await refreshAll();
      setIsLoading(false);
    };
    init();
  }, []);

  useEffect(() => {
    if (!isLoading && needsSetup) {
      setShowWizard(true);
    }
  }, [isLoading, needsSetup]);

  const refreshAll = async () => {
    try {
      await Promise.all([loadEmails(), loadCategories(), loadTemplates(), loadSettings()]);
    } catch (e) {
      console.error("Failed to load initial data", e);
    }
  };

  const loadEmails = async (page = 1) => {
    const response = await fetch(`${apiBase}/emails?status=pending&page=${page}&page_size=${emailPageSize}`);
    const data = await response.json();
    setEmails(data.data || []);
    setEmailTotal(data.total || 0);
    setEmailTotalPages(data.total_pages || 0);
    setEmailPage(data.page || 1);
    setEmailTotalCount(data.total_count || 0);
    setEmailPendingCount(data.pending_count || 0);
    if ((data.data || []).length && !selectedEmail) {
      setSelectedEmail(data.data[0]);
    }
  };

  const loadCategories = async () => {
    const response = await fetch(`${apiBase}/categories`);
    const data = await response.json();
    setCategories(data);
  };

  const loadTemplates = async () => {
    const response = await fetch(`${apiBase}/templates`);
    const data = await response.json();
    setTemplates(data);
  };

  const loadSettings = async () => {
    const response = await fetch(`${apiBase}/settings`);
    const data = await response.json();
    setSettings({ ...emptySettings, ...data.settings });
    setMailAccount(data.mail_account);
  };

  const selectEmail = (email) => {
    setSelectedEmail(email);
    setAnalysis(null);
    setReply(email.final_reply || email.ai_reply || "");
    setReplyTranslation("");
    setProcessingSuccess(false);
    setSelectedTemplateId(null);
    setView("workspace");
  };

  const runAnalysis = async () => {
    if (!selectedEmail) return;
    setProcessingStatus(prev => ({ ...prev, [selectedEmail.id]: "analyzing" }));
    try {
      const response = await fetch(`${apiBase}/emails/${selectedEmail.id}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force_ai: false })
      });
      const data = await response.json();
      setAnalysis(data);
      setReply(data.reply || "");
      setReplyTranslation("");
      // 如果有匹配的模板，选中它
      if (data.matched_template_id) {
        setSelectedTemplateId(data.matched_template_id);
      }
      await loadEmails();
    } finally {
      setProcessingStatus(prev => {
        const next = { ...prev };
        delete next[selectedEmail.id];
        return next;
      });
    }
  };

  const generateAIReply = async () => {
    if (!selectedEmail) return;
    setIsGeneratingAI(true);
    try {
      const response = await fetch(`${apiBase}/emails/${selectedEmail.id}/generate-reply`, {
        method: "POST"
      });
      const data = await response.json();
      setReply(data.reply || "");
      setReplyTranslation("");
    } finally {
      setIsGeneratingAI(false);
    }
  };

  const translateReply = async () => {
    if (!reply.trim()) return;
    setIsTranslating(true);
    try {
      const response = await fetch(`${apiBase}/emails/translate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: reply, target_lang: "zh", source_lang: "en" })
      });
      const data = await response.json();
      setReplyTranslation(data.translation || "");
    } catch (e) {
      console.error("Translation failed:", e);
    } finally {
      setIsTranslating(false);
    }
  };

  // 反向翻译：将中文翻译回英文
  const reverseTranslateReply = async () => {
    if (!replyTranslation.trim()) return;
    setIsReverseTranslating(true);
    try {
      const response = await fetch(`${apiBase}/emails/translate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: replyTranslation, target_lang: "en", source_lang: "zh" })
      });
      const data = await response.json();
      // 用翻译后的英文更新回复内容
      setReply(data.translation || "");
    } catch (e) {
      console.error("Reverse translation failed:", e);
    } finally {
      setIsReverseTranslating(false);
    }
  };

  const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  const applyVariableMapping = () => {
    const variables = analysis?.extracted_variables;
    if (!variables || Object.keys(variables).length === 0) {
      alert("暂无可映射变量，请先生成建议");
      return;
    }

    let updated = reply;
    Object.entries(variables).forEach(([key, value]) => {
      if (value === null || value === undefined || value === "") return;
      const pattern = new RegExp(`\\{${escapeRegExp(key)}\\}`, "g");
      updated = updated.replace(pattern, String(value));
    });

    setReply(updated);
    setReplyTranslation("");
  };

  const deleteEmail = async (id, e) => {
    e.stopPropagation();
    if (!confirm("确定删除该邮件？")) return;
    
    setProcessingStatus(prev => ({ ...prev, [id]: "deleting" }));
    try {
      await fetch(`${apiBase}/emails/${id}`, { method: "DELETE" });
      await loadEmails();
      if (selectedEmail?.id === id) {
        setSelectedEmail(null);
        setView("inbox");
      }
    } finally {
      setProcessingStatus(prev => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    }
  };

  const handleProcessNext = () => {
    setProcessingSuccess(false);
    setAnalysis(null);
    setReply("");
    setReplyTranslation("");
    if (emails.length > 0) {
      selectEmail(emails[0]);
    } else {
      setSelectedEmail(null);
      setView("inbox");
    }
  };

  const sendEmail = async () => {
    if (!selectedEmail) return;
    setProcessingStatus(prev => ({ ...prev, [selectedEmail.id]: "sending" }));
    try {
      await fetch(`${apiBase}/emails/${selectedEmail.id}/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reply, category_id: analysis?.category?.id })
      });
      
      setProcessingStatus(prev => ({ ...prev, [selectedEmail.id]: "sent" }));
      setProcessingSuccess(true);
      await loadEmails();
    } catch (e) {
      setProcessingStatus(prev => {
        const next = { ...prev };
        delete next[selectedEmail.id];
        return next;
      });
    }
  };

  const manualSync = async () => {
    setIsSyncing(true);
    try {
      await fetch(`${apiBase}/emails/sync`, { method: "POST" });
      await loadEmails(1);
    } finally {
      setIsSyncing(false);
    }
  };

  const saveSettings = async (event) => {
    event.preventDefault();
    setIsSavingSettings(true);
    try {
      await fetch(`${apiBase}/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings)
      });
      if (mailAccount) {
        await fetch(`${apiBase}/settings/mail-account`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(mailAccount)
        });
      }
      await loadSettings();
      setShowWizard(false);
    } finally {
      setIsSavingSettings(false);
    }
  };

  const activeCategoryName = useMemo(() => {
    const id = analysis?.category?.id || selectedEmail?.category_id;
    const category = categories.find((item) => item.id === id);
    return category?.name || "未分类";
  }, [analysis, selectedEmail, categories]);

  // 当前分类关联的模板
  const currentTemplates = useMemo(() => {
    const catId = analysis?.category?.id;
    if (!catId) return templates;
    return templates.filter(t => t.category_id === catId);
  }, [analysis?.category?.id, templates]);

  // --- 分类管理 ---
  const [editingCategory, setEditingCategory] = useState(null);
  const [categoryForm, setCategoryForm] = useState({ name: "", description: "", keywords: "", is_default: false, priority: 0 });
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [templateForm, setTemplateForm] = useState({ category_id: null, name: "", content: "", variables: "" });

  const saveCategory = async (e) => {
    e.preventDefault();
    const isNew = !editingCategory?.id;
    setCategoryOperation({ type: 'save', id: isNew ? 'new' : editingCategory.id });
    
    try {
      const method = editingCategory?.id ? "PUT" : "POST";
      const url = editingCategory?.id ? `${apiBase}/categories/${editingCategory.id}` : `${apiBase}/categories`;
      await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(categoryForm)
      });
      setEditingCategory(null);
      setCategoryForm({ name: "", description: "", keywords: "", is_default: false, priority: 0 });
      await loadCategories();
    } finally {
      setCategoryOperation({ type: null, id: null });
    }
  };

  const deleteCategory = async (id) => {
    if (!confirm("确定删除该分类？")) return;
    setCategoryOperation({ type: 'delete', id });
    try {
      await fetch(`${apiBase}/categories/${id}`, { method: "DELETE" });
      await loadCategories();
    } finally {
      setCategoryOperation({ type: null, id: null });
    }
  };

  const editCategory = (cat) => {
    setEditingCategory(cat);
    setCategoryForm({ name: cat.name, description: cat.description || "", keywords: cat.keywords || "", is_default: cat.is_default, priority: cat.priority });
  };

  // --- 模板管理 ---
  const [showTemplateDrawer, setShowTemplateDrawer] = useState(false);

  const saveTemplate = async (e) => {
    e.preventDefault();
    const isNew = !editingTemplate?.id;
    setTemplateOperation({ type: 'save', id: isNew ? 'new' : editingTemplate.id });

    try {
      const method = editingTemplate?.id ? "PUT" : "POST";
      const url = editingTemplate?.id ? `${apiBase}/templates/${editingTemplate.id}` : `${apiBase}/templates`;
      await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(templateForm)
      });
      setEditingTemplate(null);
      setTemplateForm({ category_id: null, name: "", content: "", variables: "" });
      await loadTemplates();
    } finally {
      setTemplateOperation({ type: null, id: null });
    }
  };

  const deleteTemplate = async (id) => {
    if (!confirm("确定删除该模板？")) return;
    setTemplateOperation({ type: 'delete', id });
    try {
      await fetch(`${apiBase}/templates/${id}`, { method: "DELETE" });
      await loadTemplates();
    } finally {
      setTemplateOperation({ type: null, id: null });
    }
  };

  const editTemplate = (t) => {
    setEditingTemplate(t);
    setTemplateForm({ category_id: t.category_id, name: t.name, content: t.content, variables: t.variables || "" });
    setShowTemplateDrawer(true);
  };

  const openNewTemplateDrawer = () => {
    setEditingTemplate(null);
    setTemplateForm({ category_id: null, name: "", content: "", variables: "" });
    setShowTemplateDrawer(true);
  };

  const closeTemplateDrawer = () => {
    setShowTemplateDrawer(false);
    setEditingTemplate(null);
    setTemplateForm({ category_id: null, name: "", content: "", variables: "" });
  };

  const handleDrawerSave = async (e) => {
    e.preventDefault();
    await saveTemplate(e);
    setShowTemplateDrawer(false);
  };

  const applyTemplate = (t) => {
    setReply(t.content);
    setSelectedTemplateId(t.id);
  };

  return (
    <div className="app-shell">
      {/* Setup Wizard Modal */}
      {showWizard && (
        <div className="wizard-overlay">
          <div className="wizard-modal">
            <div className="wizard-header">
              <h2>首次配置向导</h2>
              <p>完成以下配置即可开始使用</p>
            </div>
            <form className="wizard-form" onSubmit={saveSettings}>
              <div className="wizard-section">
                <h3>邮箱配置</h3>
                <div className="wizard-grid">
                  <input placeholder="邮箱账号" value={mailAccount?.email || ""} onChange={(e) => setMailAccount({ ...mailAccount, email: e.target.value })} />
                  <input placeholder="IMAP Host" value={mailAccount?.imap_host || ""} onChange={(e) => setMailAccount({ ...mailAccount, imap_host: e.target.value })} />
                  <input placeholder="IMAP Port" value={mailAccount?.imap_port || ""} onChange={(e) => setMailAccount({ ...mailAccount, imap_port: Number(e.target.value) })} />
                  <input placeholder="SMTP Host" value={mailAccount?.smtp_host || ""} onChange={(e) => setMailAccount({ ...mailAccount, smtp_host: e.target.value })} />
                  <input placeholder="SMTP Port" value={mailAccount?.smtp_port || ""} onChange={(e) => setMailAccount({ ...mailAccount, smtp_port: Number(e.target.value) })} />
                  <input placeholder="登录用户名" value={mailAccount?.username || ""} onChange={(e) => setMailAccount({ ...mailAccount, username: e.target.value })} />
                  <input placeholder="登录密码" type="password" value={mailAccount?.password || ""} onChange={(e) => setMailAccount({ ...mailAccount, password: e.target.value })} />
                </div>
              </div>
              <div className="wizard-section">
                <h3>AI 配置</h3>
                <div className="wizard-grid">
                  <input placeholder="DeepSeek API Key" value={settings.deepseek_api_key || ""} onChange={(e) => setSettings({ ...settings, deepseek_api_key: e.target.value })} />
                  <input placeholder="百度翻译 AppID" value={settings.baidu_appid || ""} onChange={(e) => setSettings({ ...settings, baidu_appid: e.target.value })} />
                  <input placeholder="百度翻译 Secret" value={settings.baidu_secret || ""} onChange={(e) => setSettings({ ...settings, baidu_secret: e.target.value })} />
                </div>
              </div>
              <Button className="primary wizard-submit" type="submit" loading={isSavingSettings}>开始使用</Button>
            </form>
          </div>
        </div>
      )}

      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">CX</div>
          <div>
            <h1>客服邮件智能回复台</h1>
            <p>本地运行 · 一键协同 · 智能建议</p>
          </div>
        </div>
        <div className="top-actions">
          <Button className="ghost" onClick={manualSync} loading={isSyncing}>手动拉取</Button>
          <Button className="setup-btn" onClick={() => setShowWizard(true)} title="配置向导">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3"/>
              <path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
            </svg>
          </Button>
          <Button className="theme-toggle" onClick={() => setTheme(theme === "light" ? "dark" : "light")}>
            {theme === "light" ? "暗色" : "亮色"}
          </Button>
        </div>
      </header>

      <nav className="nav">
        <Button className={view === "inbox" ? "active" : ""} onClick={() => setView("inbox")}>待处理</Button>
        <Button className={view === "workspace" ? "active" : ""} onClick={() => setView("workspace")}>处理台</Button>
        <Button className={view === "settings" ? "active" : ""} onClick={() => setView("settings")}>配置中心</Button>
        <Button className={view === "templates" ? "active" : ""} onClick={() => setView("templates")}>模板库</Button>
      </nav>

      <main className="main">
        {view === "inbox" && (
          <section className="panel inbox">
            <div className="panel-head">
              <h2>待处理邮件</h2>
              <span>{emailTotal} 封</span>
            </div>
            <div className="mail-list">
              {emails.map((email) => {
                const cat = categories.find((c) => c.id === email.category_id);
                const status = processingStatus[email.id];
                return (
                  <div
                    key={email.id}
                    role="button"
                    tabIndex={0}
                    className={`mail-card ${selectedEmail?.id === email.id ? "selected" : ""} ${status ? "processing" : ""}`}
                    onClick={() => selectEmail(email)}
                    onKeyDown={(e) => { if (e.key === 'Enter') selectEmail(email); }}
                  >
                    <div className="mail-info">
                      <div className="mail-header-row">
                        <h3>{email.subject || "(无主题)"}</h3>
                        {status && (
                          <span className={`status-pill ${status}`}>
                            {status === "analyzing" && "分析中"}
                            {status === "sending" && "发送中"}
                            {status === "sent" && "已发送"}
                            {status === "deleting" && "删除中"}
                          </span>
                        )}
                      </div>
                      <p>{email.sender}</p>
                      <div className="mail-time">
                        <span className="time-relative">{formatRelativeTime(email.received_at)}</span>
                        <span className="time-full">{formatFullTime(email.received_at)}</span>
                      </div>
                    </div>
                    <div className="mail-meta">
                      <span className="tag">{cat?.name || "未分类"}</span>
                      <Button
                        className="delete-btn"
                        onClick={(e) => deleteEmail(email.id, e)}
                        title="删除"
                        loading={status === "deleting"}
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="3 6 5 6 21 6"></polyline>
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                      </Button>
                    </div>
                  </div>
                );
              })}
              {!emails.length && !isLoading && <div className="empty">暂无待处理邮件</div>}
              {isLoading && <div className="empty">加载中...</div>}
            </div>

            {/* 分页控件 */}
            {emailTotalPages > 1 && (
              <div className="pagination">
                <Button
                  className="ghost small"
                  onClick={() => loadEmails(1)}
                  disabled={emailPage === 1}
                >
                  首页
                </Button>
                <Button
                  className="ghost small"
                  onClick={() => loadEmails(emailPage - 1)}
                  disabled={emailPage === 1}
                >
                  上一页
                </Button>
                <span className="page-info">
                  第 {emailPage} / {emailTotalPages} 页 ({emailTotal} 封)
                </span>
                <Button
                  className="ghost small"
                  onClick={() => loadEmails(emailPage + 1)}
                  disabled={emailPage >= emailTotalPages}
                >
                  下一页
                </Button>
                <Button
                  className="ghost small"
                  onClick={() => loadEmails(emailTotalPages)}
                  disabled={emailPage >= emailTotalPages}
                >
                  末页
                </Button>
              </div>
            )}
          </section>
        )}

        {view === "workspace" && (
          <section className="panel workspace">
            <div className="panel-head">
              <h2>邮件处理</h2>
              <span>三步完成：查看 · 选择 · 发送</span>
            </div>

            {/* 进度条 - 已处理比例 */}
            {emailTotalCount > 0 && (
              <div className="progress-section">
                <div className="progress-header">
                  <span className="progress-label">📬 处理进度</span>
                  <span className="progress-count">{emailPendingCount} / {emailTotalCount} 待处理</span>
                </div>
                <div className="progress-bar-container">
                  <div
                    className="progress-bar-fill"
                    style={{ width: `${emailTotalCount > 0 ? ((emailTotalCount - emailPendingCount) / emailTotalCount) * 100 : 0}%` }}
                  >
                    <span className="progress-sparkle">✨</span>
                  </div>
                </div>
                <p className="progress-hint">
                  {emailPendingCount === 0 ? "🎉 全部处理完成！" :
                   emailPendingCount > 30 ? "任务繁重，加油处理！" :
                   emailPendingCount > 10 ? "稳步推进中..." : "快要完成啦！"}
                </p>
              </div>
            )}

            {processingSuccess ? (
              <div className="success-view">
                <div className="success-icon">✓</div>
                <div>
                  <h3>邮件发送成功！</h3>
                  <p>该邮件已完成处理并归档。</p>
                </div>
                <Button className="primary" onClick={handleProcessNext}>处理下一封</Button>
              </div>
            ) : !selectedEmail ? (
              <div className="empty">请选择一封邮件</div>
            ) : (
              <div className="workspace-grid workspace-wide">
                <div className="mail-preview">
                  <header>
                    <h3>{selectedEmail.subject || "(无主题)"}</h3>
                    <p>{selectedEmail.sender}</p>
                    <div className="meta">
                      <span>语言：{selectedEmail.language || "未知"}</span>
                      <span>分类：{activeCategoryName}</span>
                    </div>
                  </header>
                  <article>
                    <section>
                      <h4>原文</h4>
                      <p>{selectedEmail.body_text || "(空)"}</p>
                    </section>
                    <section>
                      <h4>译文</h4>
                      <p>{selectedEmail.translation || "未翻译"}</p>
                    </section>
                  </article>
                </div>
                <div className="reply-pane reply-pane-wide">
                  <div className="ai-insight">
                    <h4>AI 推荐</h4>
                    <p>建议分类：{analysis?.category?.name || activeCategoryName}</p>
                    <p>置信度：{analysis?.confidence ? analysis.confidence.toFixed(2) : "-"}</p>
                    <p>匹配方式：{analysis?.method === "keyword" ? "关键词" : analysis?.method === "ai" ? "AI语义" : analysis?.method === "default" ? "默认" : "-"}</p>
                    {analysis?.reason && <p>分类原因：{analysis.reason}</p>}
                    <div className="reply-source-badge">
                      {analysis?.reply_source === "template" && <span className="badge template">来自模板</span>}
                      {analysis?.reply_source === "ai" && <span className="badge ai">AI生成</span>}
                    </div>
                    <Button 
                      className="primary" 
                      onClick={runAnalysis}
                      loading={processingStatus[selectedEmail.id] === "analyzing"}
                    >
                      生成建议
                    </Button>
                  </div>

                  {/* 模板选择 - 下拉框形式 */}
                  {currentTemplates.length > 0 && (
                    <div className="template-dropdown-container">
                      <label className="template-dropdown-label">选择回复模板</label>
                      <select
                        className="template-dropdown"
                        value={selectedTemplateId || ""}
                        onChange={(e) => {
                          const t = currentTemplates.find(t => t.id === Number(e.target.value));
                          if (t) applyTemplate(t);
                        }}
                      >
                        <option value="">-- 选择模板 --</option>
                        {currentTemplates.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.name}
                          </option>
                        ))}
                      </select>
                      {selectedTemplateId && (
                        <div className="template-dropdown-preview">
                          <span className="preview-label">预览：</span>
                          <span className="preview-text">
                            {currentTemplates.find(t => t.id === selectedTemplateId)?.content.substring(0, 80)}...
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* AI生成按钮 */}
                  <div className="ai-reply-action">
                    <Button className="ghost full-width" onClick={generateAIReply} loading={isGeneratingAI}>
                      让AI重新生成回复
                    </Button>
                  </div>

                  <div className="reply-editor">
                    <h4>回复内容</h4>
                    <textarea className="reply-textarea-wide" value={reply} onChange={(e) => { setReply(e.target.value); setReplyTranslation(""); }} />
                    <div className="editor-actions">
                      <span>支持变量替换，如 {"{客户姓名}"}</span>
                      <div className="editor-buttons">
                        <Button className="ghost" onClick={translateReply} disabled={isTranslating || !reply.trim()} loading={isTranslating}>
                          {isTranslating ? "翻译中..." : "翻译预览"}
                        </Button>
                        <Button className="ghost" onClick={applyVariableMapping} disabled={!reply.trim()}>
                          变量映射
                        </Button>
                        <Button className="primary" onClick={sendEmail} loading={processingStatus[selectedEmail.id] === "sending"}>
                          一键发送
                        </Button>
                      </div>
                    </div>
                  </div>

                  {/* 回复翻译预览 - 可编辑 */}
                  {replyTranslation && (
                    <div className="reply-translation-preview">
                      <h4>回复译文（中文预览）</h4>
                      <textarea
                        className="translation-textarea"
                        value={replyTranslation}
                        onChange={(e) => setReplyTranslation(e.target.value)}
                        placeholder="可在此编辑中文，修改后点击「翻译回英文」更新回复内容"
                      />
                      <div className="translation-actions">
                        <Button
                          className="accent"
                          onClick={reverseTranslateReply}
                          disabled={isReverseTranslating || !replyTranslation.trim()}
                          loading={isReverseTranslating}
                        >
                          {isReverseTranslating ? "翻译中..." : "翻译回英文 ↩"}
                        </Button>
                        <span className="translation-hint">修改中文后点击按钮更新英文回复</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </section>
        )}

        {view === "settings" && (
          <section className="panel settings">
            <div className="panel-head">
              <h2>配置中心</h2>
              <span>管理邮箱、AI和系统配置</span>
            </div>
            <form className="settings-form settings-wide" onSubmit={saveSettings}>
              <div className="form-section">
                <h3>邮箱配置</h3>
                <div className="form-grid form-grid-wide">
                  <input placeholder="邮箱账号" value={mailAccount?.email || ""} onChange={(e) => setMailAccount({ ...mailAccount, email: e.target.value })} />
                  <input placeholder="IMAP Host" value={mailAccount?.imap_host || ""} onChange={(e) => setMailAccount({ ...mailAccount, imap_host: e.target.value })} />
                  <input placeholder="IMAP Port" value={mailAccount?.imap_port || ""} onChange={(e) => setMailAccount({ ...mailAccount, imap_port: Number(e.target.value) })} />
                  <input placeholder="SMTP Host" value={mailAccount?.smtp_host || ""} onChange={(e) => setMailAccount({ ...mailAccount, smtp_host: e.target.value })} />
                  <input placeholder="SMTP Port" value={mailAccount?.smtp_port || ""} onChange={(e) => setMailAccount({ ...mailAccount, smtp_port: Number(e.target.value) })} />
                  <input placeholder="登录用户名" value={mailAccount?.username || ""} onChange={(e) => setMailAccount({ ...mailAccount, username: e.target.value })} />
                  <input placeholder="登录密码" type="password" value={mailAccount?.password || ""} onChange={(e) => setMailAccount({ ...mailAccount, password: e.target.value })} />
                </div>
              </div>

              <div className="form-section">
                <h3>AI / 翻译配置</h3>
                <div className="form-grid form-grid-wide">
                  <input placeholder="百度翻译 AppID" value={settings.baidu_appid || ""} onChange={(e) => setSettings({ ...settings, baidu_appid: e.target.value })} />
                  <input placeholder="百度翻译 Secret" value={settings.baidu_secret || ""} onChange={(e) => setSettings({ ...settings, baidu_secret: e.target.value })} />
                  <input placeholder="DeepSeek API Key" value={settings.deepseek_api_key || ""} onChange={(e) => setSettings({ ...settings, deepseek_api_key: e.target.value })} />
                  <input placeholder="DeepSeek Base URL" value={settings.deepseek_base_url || ""} onChange={(e) => setSettings({ ...settings, deepseek_base_url: e.target.value })} />
                  <input placeholder="DeepSeek Model" value={settings.deepseek_model || ""} onChange={(e) => setSettings({ ...settings, deepseek_model: e.target.value })} />
                  <input placeholder="拉取间隔(秒)" value={settings.fetch_interval || ""} onChange={(e) => setSettings({ ...settings, fetch_interval: Number(e.target.value) })} />
                </div>
              </div>

              <Button className="primary" type="submit" loading={isSavingSettings}>保存配置</Button>
            </form>

            {/* 分类管理 - 保留在设置中 */}
            <div className="form-section categories-section">
              <h3>邮件分类管理</h3>
              <p className="section-desc">配置邮件分类及关键词，用于AI分类识别。</p>
              <div className="categories-list">
                {categories.map((cat) => {
                  const catTemplates = templates.filter(t => t.category_id === cat.id);
                  return (
                    <div key={cat.id} className="category-item">
                      <div className="category-info">
                        <strong>{cat.name}</strong>
                        {cat.description && <span className="cat-desc">{cat.description}</span>}
                        {cat.keywords && <span className="cat-keywords">关键词: {cat.keywords}</span>}
                        {catTemplates.length > 0 && <span className="cat-templates">{catTemplates.length}个模板</span>}
                      </div>
                      <div className="category-actions">
                        <Button className="small" onClick={() => editCategory(cat)}>编辑</Button>
                        {!cat.is_default && (
                          <Button 
                            className="small danger" 
                            onClick={() => deleteCategory(cat.id)}
                            loading={categoryOperation.type === 'delete' && categoryOperation.id === cat.id}
                          >
                            删除
                          </Button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              <form className="category-form" onSubmit={saveCategory}>
                <h4>{editingCategory?.id ? "编辑分类" : "新增分类"}</h4>
                <div className="form-grid">
                  <input placeholder="分类名称" value={categoryForm.name} onChange={(e) => setCategoryForm({ ...categoryForm, name: e.target.value })} required />
                  <input placeholder="分类描述（AI参考）" value={categoryForm.description} onChange={(e) => setCategoryForm({ ...categoryForm, description: e.target.value })} />
                  <input placeholder="关键词（逗号分隔）" value={categoryForm.keywords} onChange={(e) => setCategoryForm({ ...categoryForm, keywords: e.target.value })} />
                  <label className="checkbox-label">
                    <input type="checkbox" checked={categoryForm.is_default} onChange={(e) => setCategoryForm({ ...categoryForm, is_default: e.target.checked })} />
                    设为默认分类
                  </label>
                </div>
                <div className="form-actions">
                  {editingCategory && <Button type="button" className="ghost" onClick={() => { setEditingCategory(null); setCategoryForm({ name: "", description: "", keywords: "", is_default: false, priority: 0 }); }}>取消</Button>}
                  <Button 
                    className="primary" 
                    type="submit"
                    loading={categoryOperation.type === 'save' && (editingCategory?.id ? categoryOperation.id === editingCategory.id : categoryOperation.id === 'new')}
                  >
                    {editingCategory?.id ? "更新" : "新增"}分类
                  </Button>
                </div>
              </form>
            </div>
          </section>
        )}

        {view === "templates" && (
          <section className="panel settings">
            <div className="panel-head">
              <h2>模板库</h2>
              <div className="panel-head-actions">
                <span>管理回复模板，为分类配置标准回复</span>
                <Button className="new-template-btn" onClick={openNewTemplateDrawer}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="5" x2="12" y2="19"></line>
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                  </svg>
                  新建模板
                </Button>
              </div>
            </div>

            <div className="template-full-list">
              {templates.map((t) => {
                const cat = categories.find(c => c.id === t.category_id);
                return (
                  <div key={t.id} className="template-full-item">
                    <div className="template-full-info">
                      <strong>{t.name}</strong>
                      <span className="template-cat-badge">{cat?.name || "未分类"}</span>
                      <p className="template-full-content">{t.content}</p>
                      {t.variables && <span className="template-vars">变量: {t.variables}</span>}
                    </div>
                    <div className="template-full-actions">
                      <Button className="small" onClick={() => editTemplate(t)}>编辑</Button>
                      <Button
                        className="small danger"
                        onClick={() => deleteTemplate(t.id)}
                        loading={templateOperation.type === 'delete' && templateOperation.id === t.id}
                      >
                        删除
                      </Button>
                    </div>
                  </div>
                );
              })}
              {!templates.length && <div className="empty">暂无模板，点击「新建模板」按钮添加</div>}
            </div>
          </section>
        )}

        {/* Template Drawer - 侧边抽屉 - 优化性能版本 */}
        <div className={`drawer-overlay ${showTemplateDrawer ? 'active' : ''}`} onClick={closeTemplateDrawer}></div>
        <div className={`drawer drawer-template ${showTemplateDrawer ? 'active' : ''}`}>
          <div className="drawer-header">
                <h3>{editingTemplate?.id ? "编辑模板" : "新建模板"}</h3>
                <button className="drawer-close" onClick={closeTemplateDrawer}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M18 6L6 18M6 6l12 12"/>
                  </svg>
                </button>
              </div>
              <form className="drawer-form" onSubmit={handleDrawerSave}>
                <div className="form-group">
                  <label>关联分类 *</label>
                  <select
                    value={templateForm.category_id || ""}
                    onChange={(e) => setTemplateForm({ ...templateForm, category_id: Number(e.target.value) })}
                    required
                  >
                    <option value="">选择关联分类</option>
                    {categories.map((c) => (<option key={c.id} value={c.id}>{c.name}</option>))}
                  </select>
                </div>
                <div className="form-group">
                  <label>模板名称 *</label>
                  <input
                    type="text"
                    placeholder="如：退款确认回复"
                    value={templateForm.name}
                    onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>变量说明</label>
                  <input
                    type="text"
                    placeholder="如：客户姓名,订单号（逗号分隔）"
                    value={templateForm.variables}
                    onChange={(e) => setTemplateForm({ ...templateForm, variables: e.target.value })}
                  />
                  <span className="form-hint">变量可在模板中使用 {"{变量名}"} 格式</span>
                </div>
                <div className="form-group">
                  <label>模板内容 *</label>
                  <textarea
                    className="drawer-textarea"
                    placeholder="模板内容（支持变量替换，如 {客户姓名}、{订单号}）"
                    value={templateForm.content}
                    onChange={(e) => setTemplateForm({ ...templateForm, content: e.target.value })}
                    required
                  />
                </div>
                <div className="drawer-actions">
                  <Button type="button" className="ghost" onClick={closeTemplateDrawer}>取消</Button>
                  <Button
                    className="primary"
                    type="submit"
                    loading={templateOperation.type === 'save' && (editingTemplate?.id ? templateOperation.id === editingTemplate.id : templateOperation.id === 'new')}
                  >
                    {editingTemplate?.id ? "更新模板" : "保存模板"}
                  </Button>
                </div>
              </form>
            </div>
      </main>
    </div>
  );
}
