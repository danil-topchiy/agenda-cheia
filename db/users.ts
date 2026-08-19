import { getDb } from ".";
import { users } from "./schema";

type Registration = {
  id: string;
  email: string;
  name: string | null;
};

export async function registerUser(registration: Registration) {
  const now = new Date().toISOString();

  await getDb()
    .insert(users)
    .values({
      id: registration.id,
      email: registration.email,
      name: registration.name,
      updatedAt: now,
    })
    .onConflictDoUpdate({
      target: users.id,
      set: {
        email: registration.email,
        name: registration.name,
        updatedAt: now,
      },
    })
    .run();
}
