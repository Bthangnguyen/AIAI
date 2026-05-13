import { load, save } from "./storage"

const SYNC_QUEUE_KEY = "offline_sync_queue"

export const SyncQueue = {
  enqueueAction(action: any) {
    const queue = load<any[]>(SYNC_QUEUE_KEY) || []
    queue.push(action)
    save(SYNC_QUEUE_KEY, queue)
  },
}
