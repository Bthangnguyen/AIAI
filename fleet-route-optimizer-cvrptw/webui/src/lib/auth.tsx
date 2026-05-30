"use client"

import { createContext, useContext, useEffect, useMemo, useState } from "react"
import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut as firebaseSignOut,
  type User,
} from "firebase/auth"
import { auth, isFirebaseConfigured } from "@/lib/firebase"

interface AuthContextValue {
  user: User | null
  loading: boolean
  configured: boolean
  signInWithGoogle: () => Promise<User | null>
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
          uid: "mock-user-12345",
          email: "guest@tripflow.ai",
          displayName: "Guest Tester",
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
