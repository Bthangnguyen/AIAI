import { useTripStore } from '../store/useTripStore';

export const useMockPlanTrip = () => {
  const setSseStage = useTripStore((state) => state.setSseStage);
  const setExtractedConstraints = useTripStore((state) => state.setExtractedConstraints);
  const setCurrentItinerary = useTripStore((state) => state.setCurrentItinerary);
  const setOriginalPrompt = useTripStore((state) => state.setOriginalPrompt);

  const startMockPlan = (prompt: string) => {
    setOriginalPrompt(prompt);
    setSseStage('intent_extraction_started');
    
    // Giả lập xử lý LLM tốn 2 giây
    setTimeout(() => {
      setSseStage('intent_extraction_completed');
      setExtractedConstraints({
        num_days: 2,
        tags: ['văn hóa', 'ẩm thực'],
        locked_pois: [],
        food_preferences: ['chay'],
        walking_tolerance: 'medium',
        preferred_pace: 'chill'
      });
    }, 2000);

    // Giả lập tìm kiếm POI bằng PostGIS tốn 1.5 giây
    setTimeout(() => setSseStage('poi_search_started'), 3500);
    setTimeout(() => setSseStage('poi_search_completed'), 4500);
    
    // Giả lập OR-Tools CVRPTW chạy tốn 3 giây
    setTimeout(() => setSseStage('optimization_started'), 5000);
    setTimeout(() => setSseStage('optimization_completed'), 8000);
    
    // Giả lập đánh giá và sinh narrative tốn 1 giây
    setTimeout(() => setSseStage('validation_completed'), 8500);
    setTimeout(() => setSseStage('narrative_completed'), 9000);

    // Hoàn thành và ném kết quả giả vào State
    setTimeout(() => {
      setSseStage('completed');
      setCurrentItinerary({
        status: 'success',
        message: 'Lộ trình Huế 2 ngày 1 đêm phong cách Chill',
        days: [
          {
            day_index: 1,
            pois: [
              { name: 'Đại Nội Huế', time: '08:00 - 10:30' },
              { name: '__rest_break__', time: '10:30 - 10:50' },
              { name: 'Chùa Thiên Mụ', time: '11:10 - 12:00' },
              { name: 'Nhà hàng chay Bồ Đề', time: '12:15 - 13:30' }
            ]
          }
        ]
      } as any);
    }, 9500);
  };

  return { startMockPlan };
};
