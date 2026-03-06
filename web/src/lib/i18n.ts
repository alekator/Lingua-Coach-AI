type Locale = "en" | "ru";

const MESSAGES: Record<Locale, Record<string, string>> = {
  en: {
    app_title: "LinguaCoach AI",
    app_tagline: "Plan - Practice - Feedback - Progress",
    nav_dashboard: "Dashboard",
    nav_session: "Daily Session",
    nav_chat: "Coach Chat",
    nav_voice: "Speaking",
    nav_translate: "Translate",
    nav_vocab: "Word Bank",
    nav_exercises: "Drills",
    nav_scenarios: "Roleplays",
    nav_grammar: "Grammar",
    nav_homework: "Homework",
    nav_profile: "Profile",
    onboarding_title: "First Launch Setup",
    onboarding_new_space_title: "New learning space detected",
    onboarding_new_space_note: "This language pair is new for you. Complete the short placement to unlock this space.",
    onboarding_start: "Start coaching placement",
    onboarding_save_key: "Save and verify key",
    scenarios_title: "Roleplay Scenarios",
    scenarios_start: "Start coached roleplay",
    scenarios_locked: "Locked by mastery",
    file_picker_choose: "Choose file",
    file_picker_empty: "No file selected",
  },
  ru: {
    app_title: "LinguaCoach AI",
    app_tagline: "План - Практика - Фидбек - Прогресс",
    nav_dashboard: "Дашборд",
    nav_session: "Сессия дня",
    nav_chat: "Чат с коучем",
    nav_voice: "Говорение",
    nav_translate: "Перевод",
    nav_vocab: "Словарь",
    nav_exercises: "Тренировки",
    nav_scenarios: "Сценарии",
    nav_grammar: "Грамматика",
    nav_homework: "Домашка",
    nav_profile: "Профиль",
    onboarding_title: "Первый запуск",
    onboarding_new_space_title: "Обнаружено новое языковое пространство",
    onboarding_new_space_note:
      "Эта языковая пара для вас новая. Пройдите короткий placement-тест, чтобы открыть пространство.",
    onboarding_start: "Запустить placement-тест",
    onboarding_save_key: "Сохранить и проверить ключ",
    scenarios_title: "Сценарии ролевой практики",
    scenarios_start: "Начать сценарий с коучем",
    scenarios_locked: "Заблокировано по mastery",
    file_picker_choose: "Выбрать файл",
    file_picker_empty: "Файл не выбран",
  },
};

export function uiLocaleFromNativeLang(nativeLang?: string | null): Locale {
  if (!nativeLang) return "en";
  return nativeLang.trim().toLowerCase().startsWith("ru") ? "ru" : "en";
}

export function t(locale: Locale, key: string): string {
  return MESSAGES[locale][key] ?? MESSAGES.en[key] ?? key;
}
