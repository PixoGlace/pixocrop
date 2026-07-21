const root = document.documentElement;
const year = document.querySelector("#current-year");
const themeColor = document.querySelector("#theme-color");
const themeToggle = document.querySelector(".theme-toggle");
const themeToggleIcon = document.querySelector(".theme-toggle-icon");
const themeLogos = document.querySelectorAll(".theme-logo");
const languageSelect = document.querySelector("#language-select");
const releaseStatus = document.querySelector("#release-status");
const assetLinks = document.querySelectorAll(".asset-link");

const latestReleaseUrl = "https://api.github.com/repos/PixoGlace/pixoCrop/releases/latest";
const latestReleasePage = "https://github.com/PixoGlace/pixoCrop/releases/latest";
const releaseState = {
    key: "download.loading",
    values: {},
};

const logoByTheme = {
    light: "static/assets/logo_white.png",
    dark: "static/assets/logo_dark.png",
};

const themeColorByTheme = {
    light: "#f7f7f5",
    dark: "#0f172a",
};

const rtlLanguages = new Set(["ar"]);

const translations = {
    fr: {
        "banner.text": "Un outil PixoGlace, libre et soigneusement emballé.",
        "banner.source": "Voir le code source",
        "language.label": "Langue",
        "nav.features": "Fonctions",
        "nav.download": "Télécharger",
        "nav.guide": "Guide",
        "nav.developers": "Développeurs",
        "nav.license": "Licence",
        "donation.kofi": "Ko-fi",
        "donation.kofiLong": "Soutenir sur Ko-fi",
        "hero.kicker": "PDF · Étiquettes · Impression",
        "hero.title": "Imprimez vos bordereaux<br><em>sans friction.</em>",
        "hero.copy": "PixoCrop détecte la zone utile d'un PDF, la recadre proprement et l'envoie à l'imprimante avec un aperçu clair.",
        "hero.download": "Télécharger PixoCrop",
        "hero.guide": "Voir comment ça marche",
        "hero.bubbleOpen": "Open source",
        "hero.bubbleClear": "Recadrage clair",
        "hero.bubblePrint": "Prêt à imprimer",
        "features.kicker": "Le flux de travail",
        "features.title": "Un petit outil pour gagner <em>beaucoup de gestes.</em>",
        "features.autoTitle": "Détection automatique",
        "features.autoCopy": "Ouvrez un PDF, PixoCrop cherche la zone de bordereau et affiche le rectangle a imprimer.",
        "features.manualTitle": "Correction manuelle",
        "features.manualCopy": "Dessinez, déplacez ou redimensionnez la zone si le document a un format particulier.",
        "features.printTitle": "Impression controlee",
        "features.printCopy": "Choisissez l'imprimante, les pages, le zoom, le recto-verso et les reglages par defaut du pilote.",
        "features.releaseTitle": "Disponible partout",
        "features.releaseCopy": "Utilisez PixoCrop sur macOS, Windows ou Linux avec un paquet prêt à installer.",
        "demo.alt": "Démonstration animée du recadrage et de l’impression avec PixoCrop",
        "workflow.kicker": "Documentation rapide",
        "workflow.title": "De l'ouverture du PDF a l'etiquette imprimee.",
        "workflow.copy": "Le parcours reste volontairement court : charger, verifier, ajuster si besoin, imprimer.",
        "workflow.step1": "Ouvrez un PDF ou deposez-le dans l'aperçu.",
        "workflow.step2": "Laissez PixoCrop detecter automatiquement la zone utile.",
        "workflow.step3": "Ajustez la marge, le rectangle ou appliquez la zone a toutes les pages.",
        "workflow.step4": "Ouvrez la fenetre d'impression et utilisez les parametres de l'imprimante ou vos propres reglages.",
        "install.kicker": "Pour les contributeurs",
        "install.title": "Développer et générer PixoCrop.",
        "install.copy": "Cette section concerne le code source. Pour utiliser simplement l’application, choisissez un installateur dans la section de téléchargement.",
        "install.releases": "Releases",
        "install.source": "Code source",
        "download.kicker": "Binaires prêts à lancer",
        "download.title": "Téléchargez PixoCrop pour <em>votre plateforme.</em>",
        "download.loading": "Recherche de la dernière version...",
        "download.ready": "Dernière version disponible : <strong>{version}</strong>",
        "download.failed": "Impossible de charger la dernière release. Les liens ouvrent GitHub.",
        "download.linuxTitle": "Executable autonome",
        "download.linuxCopy": "Archive <code>tar.gz</code> avec binaire a double-cliquer, fichier desktop et paquet Debian.",
        "download.windowsTitle": "Installateur Windows",
        "download.windowsCopy": "Installateur graphique ou archive ZIP pour Windows x64.",
        "download.macosTitle": "DMG macOS",
        "download.macosCopy": "Image DMG avec glisser-deposer vers Applications, plus archives ZIP de secours.",
        "legal.kicker": "Libre, mais protege",
        "legal.title": "Le code circule, la marque reste claire.",
        "legal.gpl": "Le code source est publie sous GNU General Public License v3.0.",
        "legal.copyright": "Les droits du projet sont attribues a PixoGlace.",
        "legal.trademarksTitle": "Marques",
        "legal.trademarks": "Les noms, logos, icones et l'identite visuelle restent reserves.",
        "legal.donation": "Soutenez le developpement via Ko-fi.",
        "join.kicker": "Projet PixoGlace",
        "join.title": "Un outil simple, ouvert, et pret a evoluer.",
        "join.copy": "Contribuez, signalez un souci d'impression ou proposez un format de bordereau a mieux detecter.",
        "join.issue": "Ouvrir une issue",
        "footer.project": "Un projet PixoGlace.",
        "footer.legal": "GPL-3.0 pour le code. Marques reservees.",
        "theme.dark": "Activer le theme sombre",
        "theme.light": "Activer le theme clair",
    },
    en: {
        "banner.text": "A carefully packaged open source PixoGlace tool.",
        "banner.source": "View source code",
        "language.label": "Language",
        "nav.features": "Features",
        "nav.download": "Download",
        "nav.guide": "Guide",
        "nav.developers": "Developers",
        "nav.license": "License",
        "donation.kofi": "Ko-fi",
        "donation.kofiLong": "Support on Ko-fi",
        "hero.kicker": "PDF · Labels · Printing",
        "hero.title": "Print shipping labels<br><em>without friction.</em>",
        "hero.copy": "PixoCrop detects the useful area of a PDF, crops it cleanly, and sends it to the printer with a clear preview.",
        "hero.download": "Download PixoCrop",
        "hero.guide": "See how it works",
        "hero.bubbleOpen": "Open source",
        "hero.bubbleClear": "Clear cropping",
        "hero.bubblePrint": "Ready to print",
        "features.kicker": "Workflow",
        "features.title": "A small tool that saves <em>a lot of clicks.</em>",
        "features.autoTitle": "Automatic detection",
        "features.autoCopy": "Open a PDF and PixoCrop finds the label area, then shows the rectangle to print.",
        "features.manualTitle": "Manual correction",
        "features.manualCopy": "Draw or move the area when a document uses a particular layout.",
        "features.printTitle": "Controlled printing",
        "features.printCopy": "Choose the printer, pages, zoom, duplex mode and driver defaults.",
        "features.releaseTitle": "Available everywhere",
        "features.releaseCopy": "Use PixoCrop on macOS, Windows, or Linux with a ready-to-install package.",
        "demo.alt": "Animated demonstration of cropping and printing with PixoCrop",
        "workflow.kicker": "Quick documentation",
        "workflow.title": "From opening the PDF to a printed label.",
        "workflow.copy": "The flow stays intentionally short: load, check, adjust if needed, print.",
        "workflow.step1": "Open a PDF or drop it into the preview.",
        "workflow.step2": "Let PixoCrop automatically detect the useful area.",
        "workflow.step3": "Adjust the margin, rectangle, or apply the area to every page.",
        "workflow.step4": "Open the print window and use printer defaults or your own settings.",
        "install.kicker": "For contributors",
        "install.title": "Develop and build PixoCrop.",
        "install.copy": "This section is about the source code. To simply use the application, choose an installer from the download section.",
        "install.releases": "Releases",
        "install.source": "Source code",
        "download.kicker": "Ready-to-run binaries",
        "download.title": "Download PixoCrop for <em>your platform.</em>",
        "download.loading": "Looking for the latest version...",
        "download.ready": "Latest available version: <strong>{version}</strong>",
        "download.failed": "Unable to load the latest release. Links open GitHub.",
        "download.linuxTitle": "Standalone executable",
        "download.linuxCopy": "<code>tar.gz</code> archive with a double-click binary, desktop file and Debian package.",
        "download.windowsTitle": "Windows installer",
        "download.windowsCopy": "Graphical installer or ZIP archive for Windows x64.",
        "download.macosTitle": "macOS DMG",
        "download.macosCopy": "DMG image with drag-and-drop to Applications, plus fallback ZIP archives.",
        "legal.kicker": "Open, but protected",
        "legal.title": "The code can travel, the brand stays clear.",
        "legal.gpl": "The source code is published under GNU General Public License v3.0.",
        "legal.copyright": "Project rights are assigned to PixoGlace.",
        "legal.trademarksTitle": "Trademarks",
        "legal.trademarks": "Names, logos, icons and visual identity remain reserved.",
        "legal.donation": "Support development through Ko-fi.",
        "join.kicker": "PixoGlace project",
        "join.title": "A simple, open tool ready to evolve.",
        "join.copy": "Contribute, report a printing issue, or suggest a shipping label format to detect better.",
        "join.issue": "Open an issue",
        "footer.project": "A PixoGlace project.",
        "footer.legal": "GPL-3.0 for code. Trademarks reserved.",
        "theme.dark": "Enable dark theme",
        "theme.light": "Enable light theme",
    },
    ar: {
        "banner.text": "أداة مفتوحة المصدر من PixoGlace ومجهزة بعناية.",
        "banner.source": "عرض الكود المصدري",
        "language.label": "اللغة",
        "nav.features": "الميزات",
        "nav.download": "التنزيل",
        "nav.guide": "الدليل",
        "nav.developers": "المطورون",
        "nav.license": "الترخيص",
        "donation.kofi": "Ko-fi",
        "donation.kofiLong": "ادعم عبر Ko-fi",
        "hero.kicker": "PDF · ملصقات · طباعة",
        "hero.title": "اطبع ملصقات الشحن<br><em>بلا تعقيد.</em>",
        "hero.copy": "يكتشف PixoCrop المنطقة المفيدة في ملف PDF، ويقصها بدقة، ثم يرسلها إلى الطابعة مع معاينة واضحة.",
        "hero.download": "تنزيل PixoCrop",
        "hero.guide": "شاهد طريقة العمل",
        "hero.bubbleOpen": "مفتوح المصدر",
        "hero.bubbleClear": "قص واضح",
        "hero.bubblePrint": "جاهز للطباعة",
        "features.kicker": "سير العمل",
        "features.title": "أداة صغيرة توفر <em>الكثير من الخطوات.</em>",
        "features.autoTitle": "اكتشاف تلقائي",
        "features.autoCopy": "افتح ملف PDF وسيجد PixoCrop منطقة الملصق ويعرض المستطيل المطلوب طباعته.",
        "features.manualTitle": "تصحيح يدوي",
        "features.manualCopy": "ارسم المنطقة أو انقلها عندما يستخدم المستند تنسيقاً خاصاً.",
        "features.printTitle": "طباعة مضبوطة",
        "features.printCopy": "اختر الطابعة والصفحات والتكبير والطباعة المزدوجة وإعدادات برنامج التشغيل.",
        "features.releaseTitle": "متاح في كل مكان",
        "features.releaseCopy": "استخدم PixoCrop على macOS أو Windows أو Linux مع حزمة جاهزة للتثبيت.",
        "demo.alt": "عرض متحرك للقص والطباعة باستخدام PixoCrop",
        "workflow.kicker": "توثيق سريع",
        "workflow.title": "من فتح PDF إلى ملصق مطبوع.",
        "workflow.copy": "المسار قصير عمداً: تحميل، تحقق، تعديل عند الحاجة، ثم طباعة.",
        "workflow.step1": "افتح ملف PDF أو أسقطه في المعاينة.",
        "workflow.step2": "دع PixoCrop يكتشف المنطقة المفيدة تلقائياً.",
        "workflow.step3": "عدّل الهامش أو المستطيل أو طبق المنطقة على كل الصفحات.",
        "workflow.step4": "افتح نافذة الطباعة واستخدم إعدادات الطابعة أو إعداداتك الخاصة.",
        "install.kicker": "للمساهمين",
        "install.title": "تطوير وبناء PixoCrop.",
        "install.copy": "هذا القسم مخصص للكود المصدري. لاستخدام التطبيق فقط، اختر برنامج تثبيت من قسم التنزيل.",
        "install.releases": "الإصدارات",
        "install.source": "الكود المصدري",
        "download.kicker": "ملفات جاهزة للتشغيل",
        "download.title": "نزّل PixoCrop <em>لمنصتك.</em>",
        "download.loading": "جارٍ البحث عن أحدث إصدار...",
        "download.ready": "أحدث إصدار متاح: <strong>{version}</strong>",
        "download.failed": "تعذر تحميل أحدث إصدار. الروابط تفتح GitHub.",
        "download.linuxTitle": "ملف مستقل",
        "download.linuxCopy": "أرشيف <code>tar.gz</code> مع ملف قابل للتشغيل وملف سطح مكتب وحزمة Debian.",
        "download.windowsTitle": "مثبت Windows",
        "download.windowsCopy": "مثبت رسومي أو أرشيف ZIP لنظام Windows x64.",
        "download.macosTitle": "ملف DMG لـ macOS",
        "download.macosCopy": "صورة DMG مع السحب إلى Applications بالإضافة إلى أرشيفات ZIP احتياطية.",
        "legal.kicker": "مفتوح ومحمي",
        "legal.title": "الكود يمكن أن ينتشر، والعلامة تبقى واضحة.",
        "legal.gpl": "الكود المصدري منشور تحت رخصة GNU GPL v3.0.",
        "legal.copyright": "حقوق المشروع مخصصة لـ PixoGlace.",
        "legal.trademarksTitle": "العلامات",
        "legal.trademarks": "الأسماء والشعارات والأيقونات والهوية البصرية محفوظة.",
        "legal.donation": "ادعم التطوير عبر Ko-fi.",
        "join.kicker": "مشروع PixoGlace",
        "join.title": "أداة بسيطة ومفتوحة وجاهزة للتطور.",
        "join.copy": "ساهم، أبلغ عن مشكلة طباعة، أو اقترح تنسيق ملصق شحن لتحسين اكتشافه.",
        "join.issue": "افتح بلاغاً",
        "footer.project": "مشروع من PixoGlace.",
        "footer.legal": "الكود تحت GPL-3.0. العلامات محفوظة.",
        "theme.dark": "تفعيل المظهر الداكن",
        "theme.light": "تفعيل المظهر الفاتح",
    },
    zh: {
        "banner.text": "一个精心打包的 PixoGlace 开源工具。",
        "banner.source": "查看源代码",
        "language.label": "语言",
        "nav.features": "功能",
        "nav.download": "下载",
        "nav.guide": "使用指南",
        "nav.developers": "开发者",
        "nav.license": "许可证",
        "donation.kofi": "Ko-fi",
        "donation.kofiLong": "在 Ko-fi 上支持",
        "hero.kicker": "PDF · 标签 · 打印",
        "hero.title": "轻松打印<br><em>运单标签。</em>",
        "hero.copy": "PixoCrop 会检测 PDF 中的有效区域，干净裁剪，并通过清晰预览发送到打印机。",
        "hero.download": "下载 PixoCrop",
        "hero.guide": "查看使用方法",
        "hero.bubbleOpen": "开源",
        "hero.bubbleClear": "清晰裁剪",
        "hero.bubblePrint": "即刻打印",
        "features.kicker": "工作流程",
        "features.title": "一个小工具，省下<em>很多步骤。</em>",
        "features.autoTitle": "自动检测",
        "features.autoCopy": "打开 PDF，PixoCrop 会找到标签区域并显示要打印的矩形。",
        "features.manualTitle": "手动修正",
        "features.manualCopy": "如果文档格式特殊，可以绘制或移动打印区域。",
        "features.printTitle": "可控打印",
        "features.printCopy": "选择打印机、页面、缩放、双面以及驱动默认设置。",
        "features.releaseTitle": "支持多个平台",
        "features.releaseCopy": "通过可直接安装的软件包，在 macOS、Windows 或 Linux 上使用 PixoCrop。",
        "demo.alt": "使用 PixoCrop 进行裁剪和打印的动画演示",
        "workflow.kicker": "快速文档",
        "workflow.title": "从打开 PDF 到打印标签。",
        "workflow.copy": "流程刻意保持简短：加载、检查、需要时调整，然后打印。",
        "workflow.step1": "打开 PDF 或拖放到预览区。",
        "workflow.step2": "让 PixoCrop 自动检测有效区域。",
        "workflow.step3": "调整边距、矩形，或将区域应用到所有页面。",
        "workflow.step4": "打开打印窗口，使用打印机默认设置或自定义设置。",
        "install.kicker": "面向贡献者",
        "install.title": "开发并构建 PixoCrop。",
        "install.copy": "本节介绍源代码。若只需使用应用程序，请在下载区域选择安装程序。",
        "install.releases": "发布版本",
        "install.source": "源代码",
        "download.kicker": "可直接运行的二进制文件",
        "download.title": "为<em>你的平台</em>下载 PixoCrop。",
        "download.loading": "正在查找最新版本...",
        "download.ready": "最新可用版本：<strong>{version}</strong>",
        "download.failed": "无法加载最新 release。链接将打开 GitHub。",
        "download.linuxTitle": "独立可执行文件",
        "download.linuxCopy": "<code>tar.gz</code> 归档，包含可双击二进制、桌面文件和 Debian 包。",
        "download.windowsTitle": "Windows 安装器",
        "download.windowsCopy": "Windows x64 图形安装器或 ZIP 归档。",
        "download.macosTitle": "macOS DMG",
        "download.macosCopy": "可拖到 Applications 的 DMG 镜像，并提供 ZIP 备用包。",
        "legal.kicker": "开放但受保护",
        "legal.title": "代码可以流通，品牌保持清晰。",
        "legal.gpl": "源代码以 GNU GPL v3.0 发布。",
        "legal.copyright": "项目权利归 PixoGlace。",
        "legal.trademarksTitle": "商标",
        "legal.trademarks": "名称、标志、图标和视觉识别均保留。",
        "legal.donation": "通过 Ko-fi 支持开发。",
        "join.kicker": "PixoGlace 项目",
        "join.title": "简单、开放，并准备继续发展的工具。",
        "join.copy": "参与贡献、报告打印问题，或建议更好检测的运单格式。",
        "join.issue": "提交 issue",
        "footer.project": "PixoGlace 项目。",
        "footer.legal": "代码 GPL-3.0。商标保留。",
        "theme.dark": "启用深色主题",
        "theme.light": "启用浅色主题",
    },
};

if (year) {
    year.textContent = String(new Date().getFullYear());
}

function preferredTheme() {
    const storedTheme = localStorage.getItem("pixocrop-theme");

    if (storedTheme === "light" || storedTheme === "dark") {
        return storedTheme;
    }

    if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
        return "dark";
    }

    return "light";
}

function currentLanguage() {
    const storedLanguage = localStorage.getItem("pixocrop-language");
    if (storedLanguage && translations[storedLanguage]) {
        return storedLanguage;
    }
    const browserLanguage = navigator.language?.slice(0, 2);
    return translations[browserLanguage] ? browserLanguage : "fr";
}

function text(key) {
    const language = root.dataset.language || "fr";
    return translations[language]?.[key] || translations.fr[key] || key;
}

function applyTranslations(language) {
    const nextLanguage = translations[language] ? language : "fr";
    root.dataset.language = nextLanguage;
    root.lang = nextLanguage;
    root.dir = rtlLanguages.has(nextLanguage) ? "rtl" : "ltr";

    document.querySelectorAll("[data-i18n]").forEach((node) => {
        node.textContent = text(node.dataset.i18n);
    });

    document.querySelectorAll("[data-i18n-html]").forEach((node) => {
        node.innerHTML = text(node.dataset.i18nHtml);
    });

    document.querySelectorAll("[data-i18n-alt]").forEach((node) => {
        node.setAttribute("alt", text(node.dataset.i18nAlt));
    });

    if (languageSelect) {
        languageSelect.value = nextLanguage;
        languageSelect.setAttribute("aria-label", text("language.label"));
    }

    applyTheme(root.dataset.theme || preferredTheme());
}

function applyTheme(theme) {
    const nextTheme = theme === "dark" ? "dark" : "light";
    root.dataset.theme = nextTheme;

    if (themeColor) {
        themeColor.setAttribute("content", themeColorByTheme[nextTheme]);
    }

    themeLogos.forEach((logo) => {
        logo.setAttribute("src", logoByTheme[nextTheme]);
    });

    if (themeToggle) {
        const isDark = nextTheme === "dark";
        themeToggle.setAttribute("aria-pressed", String(isDark));
        themeToggle.setAttribute(
            "aria-label",
            isDark ? text("theme.light") : text("theme.dark"),
        );
    }

    if (themeToggleIcon) {
        themeToggleIcon.textContent = nextTheme === "dark" ? "☼" : "☾";
    }
}

function setReleaseStatus(key, values = {}) {
    releaseState.key = key;
    releaseState.values = values;
    if (!releaseStatus) {
        return;
    }
    let content = text(key);
    Object.entries(values).forEach(([name, value]) => {
        content = content.replace(`{${name}}`, value);
    });
    releaseStatus.innerHTML = content;
}

function updateAssetLinks(assets) {
    assetLinks.forEach((link) => {
        const pattern = link.dataset.assetPattern;
        const asset = assets.find((candidate) => candidate.name.includes(pattern));
        if (!asset) {
            link.href = latestReleasePage;
            link.removeAttribute("aria-disabled");
            return;
        }
        link.href = asset.browser_download_url;
        link.removeAttribute("aria-disabled");
    });
}

async function loadLatestRelease() {
    setReleaseStatus("download.loading");
    try {
        const response = await fetch(latestReleaseUrl, {
            headers: { Accept: "application/vnd.github+json" },
        });
        if (!response.ok) {
            throw new Error(`GitHub returned ${response.status}`);
        }
        const release = await response.json();
        updateAssetLinks(release.assets || []);
        setReleaseStatus("download.ready", { version: release.tag_name || release.name || "latest" });
    } catch {
        assetLinks.forEach((link) => {
            if (!link.href) {
                link.href = latestReleasePage;
            }
        });
        setReleaseStatus("download.failed");
    }
}

applyTheme(preferredTheme());
applyTranslations(currentLanguage());
loadLatestRelease();

themeToggle?.addEventListener("click", () => {
    const nextTheme = root.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem("pixocrop-theme", nextTheme);
    applyTheme(nextTheme);
});

languageSelect?.addEventListener("change", (event) => {
    const nextLanguage = event.target.value;
    localStorage.setItem("pixocrop-language", nextLanguage);
    applyTranslations(nextLanguage);
    setReleaseStatus(releaseState.key, releaseState.values);
});
