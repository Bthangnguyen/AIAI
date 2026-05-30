import { vi } from "vitest"

vi.mock("@/lib/firebase", () => ({
  auth: {
    currentUser: null,
    onAuthStateChanged: vi.fn(),
    signInWithEmailAndPassword: vi.fn(),
    createUserWithEmailAndPassword: vi.fn(),
    signOut: vi.fn(),
  },
  db: {},
  isFirebaseConfigured: vi.fn(() => false),
}))
