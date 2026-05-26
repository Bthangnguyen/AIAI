"use client"

const examples = [
  "Huế 3 ngày, ngân sách 1 triệu",
  "Đại Nội, cafe muối, ăn chay",
  "Food tour Huế cuối tuần",
  "Đi nhẹ nhàng cùng gia đình",
]

export function ExamplePromptChips({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="mt-6 flex flex-wrap justify-center gap-2">
      {examples.map((example) => (
        <button key={example} type="button" onClick={() => onPick(example)} className="rounded-full border border-orange-200 bg-white/78 px-4 py-2 text-sm font-bold text-orange-950/70 shadow-lg shadow-orange-950/5 backdrop-blur transition hover:border-orange-400 hover:text-orange-600">
          {example}
        </button>
      ))}
    </div>
  )
}

