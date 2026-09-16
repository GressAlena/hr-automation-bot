-- Схема применена в проекте hr-automation через Supabase-миграции.
-- Файл хранится в репозитории как справочная копия схемы.

create extension if not exists pgcrypto;

create table vacancies (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    description text not null,
    status text not null default 'open',
    created_by bigint,
    created_at timestamptz not null default now()
);

create table candidates (
    id uuid primary key default gen_random_uuid(),
    vacancy_id uuid not null references vacancies(id) on delete cascade,
    file_name text,
    resume_text text not null,
    score int,
    summary text,
    strengths text,
    gaps text,
    recommendation text,
    status text not null default 'new',
    uploaded_by bigint,
    created_at timestamptz not null default now()
);

create index candidates_vacancy_id_idx on candidates(vacancy_id);
create index candidates_score_idx on candidates(vacancy_id, score desc);

-- Память LangChain-агента на чат: история диалога и ещё не оценённое резюме,
-- ожидающее, к какой вакансии его отнести.
create table chat_sessions (
    chat_id bigint primary key,
    history jsonb not null default '[]'::jsonb,
    pending_resume jsonb,
    updated_at timestamptz not null default now()
);

-- RLS включён: доступ к данным только через service_role ключ (используется ботом),
-- анонимный/публичный ключ доступа не имеет.
alter table vacancies enable row level security;
alter table candidates enable row level security;
alter table chat_sessions enable row level security;
