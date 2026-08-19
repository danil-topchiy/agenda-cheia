import { sql } from "drizzle-orm";
import { index, integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

const timestamps = {
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  updatedAt: text("updated_at").notNull().default(sql`CURRENT_TIMESTAMP`),
};

export const users = sqliteTable("users", {
  id: text("id").primaryKey(),
  email: text("email").notNull().unique(),
  name: text("name"),
  ...timestamps,
});

export const clients = sqliteTable(
  "clients",
  {
    id: text("id").primaryKey(),
    userId: text("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    name: text("name").notNull(),
    phone: text("phone"),
    email: text("email"),
    notes: text("notes").notNull().default(""),
    status: text("status", { enum: ["active", "waiting", "inactive"] })
      .notNull()
      .default("active"),
    ...timestamps,
  },
  (table) => [index("idx_clients_user_id").on(table.userId)],
);

export const schedule = sqliteTable(
  "schedule",
  {
    id: text("id").primaryKey(),
    userId: text("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    clientId: text("client_id")
      .notNull()
      .references(() => clients.id, { onDelete: "cascade" }),
    service: text("service").notNull(),
    professional: text("professional"),
    startsAt: text("starts_at").notNull(),
    durationMinutes: integer("duration_minutes").notNull().default(60),
    priceCents: integer("price_cents"),
    status: text("status", {
      enum: ["scheduled", "confirmed", "cancelled", "completed", "rescheduled"],
    })
      .notNull()
      .default("scheduled"),
    rescheduledFromId: text("rescheduled_from_id"),
    notes: text("notes").notNull().default(""),
    ...timestamps,
  },
  (table) => [
    index("idx_schedule_user_starts_at").on(table.userId, table.startsAt),
    index("idx_schedule_client_id").on(table.clientId),
  ],
);
