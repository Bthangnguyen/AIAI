/**
 * Tầng 3: Security Tests — No hardcoded secrets in source
 */
import * as fs from "fs"
import * as path from "path"

const APP_DIR = path.resolve(__dirname, "../../app")

// Recursively get all .ts and .tsx files
function getSourceFiles(dir: string): string[] {
  const files: string[] = []
  const entries = fs.readdirSync(dir, { withFileTypes: true })
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory() && !entry.name.startsWith(".")) {
      files.push(...getSourceFiles(fullPath))
    } else if (entry.isFile() && /\.(tsx?|js)$/.test(entry.name)) {
      files.push(fullPath)
    }
  }
  return files
}

describe("Security — No hardcoded secrets", () => {
  const sourceFiles = getSourceFiles(APP_DIR)

  it("no Mapbox token hardcoded in source files", () => {
    const violations: string[] = []
    for (const file of sourceFiles) {
      const content = fs.readFileSync(file, "utf8")
      // Mapbox tokens start with pk.eyJ1
      if (content.includes("pk.eyJ1") && !file.includes(".env")) {
        violations.push(path.relative(APP_DIR, file))
      }
    }
    expect(violations).toEqual([])
  })

  it("no OpenAI API key hardcoded in source files", () => {
    const violations: string[] = []
    for (const file of sourceFiles) {
      const content = fs.readFileSync(file, "utf8")
      if (content.includes("sk-") && content.includes("openai")) {
        violations.push(path.relative(APP_DIR, file))
      }
    }
    expect(violations).toEqual([])
  })

  it("no Firebase key hardcoded in source files", () => {
    const violations: string[] = []
    for (const file of sourceFiles) {
      const content = fs.readFileSync(file, "utf8")
      if (/AIza[a-zA-Z0-9_-]{35}/.test(content)) {
        violations.push(path.relative(APP_DIR, file))
      }
    }
    expect(violations).toEqual([])
  })
})
