"use client"

import { createContext, useContext, useEffect, useMemo, useState } from "react"
import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut as firebaseSignOut,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  updateProfile,
  sendPasswordResetEmail,
  type User,
} from "firebase/auth"
import { auth, isFirebaseConfigured } from "@/lib/firebase"

interface AuthContextValue {
  user: User | null
  loading: boolean
  configured: boolean
  signInWithGoogle: () => Promise<User | null>
  signInWithEmail: (email: string, pass: string) => Promise<User | null>
  signUpWithEmail: (email: string, pass: string, name: string) => Promise<User | null>
  sendPasswordReset: (email: string) => Promise<void>
  signInAsGuest: () => Promise<User | null>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const configured = isFirebaseConfigured() && !!auth
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(configured)

  useEffect(() => {
    if (!configured || !auth) {
      setLoading(false)
      return
    }
    return onAuthStateChanged(auth, (nextUser) => {
      setUser(nextUser)
      setLoading(false)
    })
  }, [configured])

  const value = useMemo<AuthContextValue>(() => ({
    user,
    loading,
    configured,
    async signInWithGoogle() {
      if (!configured || !auth) {
        const mockUser = {
          uid: "mock-google-user",
          email: "google-tester@tripflow.ai",
          displayName: "Google Tester",
          photoURL: "https://lh3.googleusercontent.com/a/default-user=s96-c",
          emailVerified: true,
          isAnonymous: false,
          metadata: {},
          providerData: [],
          refreshToken: "mock-refresh-token",
          tenantId: null,
          delete: async () => {},
          getIdToken: async () => "mock-id-token",
          getIdTokenResult: async () => ({} as any),
          reload: async () => {},
          toJSON: () => ({}),
          phoneNumber: null,
          providerId: "google.com",
        } as unknown as User
        setUser(mockUser)
        return mockUser
      }
      const provider = new GoogleAuthProvider()
      provider.setCustomParameters({ prompt: "select_account" })
      const result = await signInWithPopup(auth, provider)
      setUser(result.user)
      return result.user
    },

    async signInWithEmail(email, pass) {
      if (!configured || !auth) {
        const mockUser = {
          uid: `mock-email-user-${Buffer.from(email).toString("hex").slice(0, 8)}`,
          email: email,
          displayName: email.split("@")[0].toUpperCase(),
          photoURL: "https://lh3.googleusercontent.com/a/default-user=s96-c",
          emailVerified: true,
          isAnonymous: false,
          metadata: {},
          providerData: [],
          refreshToken: "mock-refresh-token",
          tenantId: null,
          delete: async () => {},
          getIdToken: async () => "mock-id-token",
          getIdTokenResult: async () => ({} as any),
          reload: async () => {},
          toJSON: () => ({}),
          phoneNumber: null,
          providerId: "password",
        } as unknown as User
        setUser(mockUser)
        return mockUser
      }
      const result = await signInWithEmailAndPassword(auth, email, pass)
      setUser(result.user)
      return result.user
    },

    async signUpWithEmail(email, pass, name) {
      if (!configured || !auth) {
        const mockUser = {
          uid: `mock-email-user-${Buffer.from(email).toString("hex").slice(0, 8)}`,
          email: email,
          displayName: name || email.split("@")[0].toUpperCase(),
          photoURL: "https://lh3.googleusercontent.com/a/default-user=s96-c",
          emailVerified: true,
          isAnonymous: false,
          metadata: {},
          providerData: [],
          refreshToken: "mock-refresh-token",
          tenantId: null,
          delete: async () => {},
          getIdToken: async () => "mock-id-token",
          getIdTokenResult: async () => ({} as any),
          reload: async () => {},
          toJSON: () => ({}),
          phoneNumber: null,
          providerId: "password",
        } as unknown as User
        setUser(mockUser)
        return mockUser
      }
      const result = await createUserWithEmailAndPassword(auth, email, pass)
      if (result.user) {
        await updateProfile(result.user, { displayName: name })
      }
      setUser(result.user)
      return result.user
    },

    async sendPasswordReset(email) {
      if (!configured || !auth) {
        console.log(`[Mock reset link sent to]: ${email}`)
        return
      }
      await sendPasswordResetEmail(auth, email)
    },

    async signInAsGuest() {
      // Cho phép bypass đăng nhập dưới quyền Khách trải nghiệm
      const mockGuest = {
        uid: "mock-guest-bypass-999",
        email: "guest.tester@tripflow.ai",
        displayName: "Khách Trải Nghiệm 👤",
        photoURL: "https://lh3.googleusercontent.com/a/default-user=s96-c",
        emailVerified: true,
        isAnonymous: true,
        metadata: {},
        providerData: [],
        refreshToken: "mock-refresh-token",
        tenantId: null,
        delete: async () => {},
        getIdToken: async () => "mock-id-token",
        getIdTokenResult: async () => ({} as any),
        reload: async () => {},
        toJSON: () => ({}),
        phoneNumber: null,
        providerId: "anonymous",
      } as unknown as User
      setUser(mockGuest)
      return mockGuest
    },

    async signOut() {
      if (!configured || !auth) {
        setUser(null)
        return
      }
      await firebaseSignOut(auth)
      setUser(null)
    },
  }), [configured, loading, user])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error("useAuth must be used inside AuthProvider")
  return value
}
