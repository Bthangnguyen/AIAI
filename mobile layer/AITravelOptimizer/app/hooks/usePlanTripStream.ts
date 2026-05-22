import EventSource, { EventSourceListener } from 'react-native-sse';
import { useTripStore } from '../store/useTripStore';
import { SSEStage } from '../types/api';

const GATEWAY_API_URL = 'http://localhost:8001'; // Thay đổi URL này trên môi trường thực tế

export const usePlanTripStream = () => {
  const setSseStage = useTripStore((state) => state.setSseStage);
  const setExtractedConstraints = useTripStore((state) => state.setExtractedConstraints);
  const setCurrentItinerary = useTripStore((state) => state.setCurrentItinerary);

  const startStreaming = (prompt: string) => {
    setSseStage('intent_extraction_started');

    // Mở kết nối SSE
    const es = new EventSource(`${GATEWAY_API_URL}/api/v1/trip/plan_trip_stream`, {
      headers: {
        'Content-Type': 'application/json',
      },
      method: 'POST',
      body: JSON.stringify({ user_prompt: prompt }),
    });

    const listener: EventSourceListener = (event) => {
      if (event.type === 'message' && event.data) {
        try {
          const data = JSON.parse(event.data);
          
          if (data.stage) {
            setSseStage(data.stage as SSEStage);
          }

          if (data.stage === 'intent_extraction_completed' && data.contract) {
            setExtractedConstraints(data.contract);
          }

          if (data.stage === 'completed' && data.result) {
            setCurrentItinerary(data.result);
            es.close(); // Đóng kết nối khi hoàn thành
          }

          if (data.stage === 'error') {
            console.error('Lỗi từ Server:', data.message);
            es.close();
          }
        } catch (error) {
          console.error('Lỗi parse JSON từ SSE:', error);
        }
      } else if (event.type === 'error') {
        console.error('Lỗi kết nối SSE:', event.message);
        setSseStage('error');
        es.close();
      }
    };

    es.addEventListener('message', listener);
    es.addEventListener('error', listener);

    return () => {
      es.removeAllEventListeners();
      es.close();
    };
  };

  return { startStreaming };
};
