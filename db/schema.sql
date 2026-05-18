create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  password_hash text not null,
  full_name text not null,
  created_at timestamptz not null default now()
);

create table if not exists guests (
  id uuid primary key default gen_random_uuid(),
  full_name text not null,
  enabled boolean not null default true,
  note text,
  face_image_path text,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now()
);

create table if not exists registration_links (
  id uuid primary key default gen_random_uuid(),
  token text not null unique,
  guest_id uuid not null references guests(id) on delete cascade,
  expires_at timestamptz not null,
  used boolean not null default false,
  created_by uuid references users(id) on delete set null,
  created_at timestamptz not null default now(),
  used_at timestamptz
);

create table if not exists notifications (
  id uuid primary key default gen_random_uuid(),
  kind text not null,
  message text not null,
  is_read boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists idx_registration_links_token on registration_links(token);
create index if not exists idx_notifications_created_at on notifications(created_at desc);
