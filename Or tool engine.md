Đúng rồi bro. Nếu tổng hợp hết paper \+ góc product, mình sẽ xếp **độ ưu tiên để tạo chuyến đi hài lòng nhất** như này:

## **Priority 0 — Không được sai: tính khả thi**

Đây là tầng **bắt buộc**. Lịch có hay cỡ nào mà sai tầng này thì user vẫn bực.

| Yếu tố | Vì sao quan trọng |
| ----- | ----- |
| Đúng thời gian mở cửa | Không thể xếp user đến POI lúc đã đóng cửa |
| Thời gian di chuyển thật | Không được lịch ảo kiểu 15 phút đi qua nửa thành phố |
| Thời lượng tham quan hợp lý | Đại Nội không thể chỉ cho 20 phút |
| Không vượt tổng thời gian mỗi ngày | Tránh lịch quá dày, hành xác |
| Budget không vượt quá | Nhất là user có ngân sách rõ |
| Locked POIs phải được giữ | User đã chỉ định thì phải ưu tiên cao |
| Đúng ngày / số ngày / điểm xuất phát | Sai là fail ngay |

Nhánh **Tourist Trip Design Problem** cũng đặt bài toán là chọn POI để tối đa hóa hài lòng, nhưng vẫn phải xét distance, visit duration, opening hours, entrance fees, weather và daily sightseeing time. ([ResearchGate](https://www.researchgate.net/publication/271921760_A_survey_on_algorithmic_approaches_for_solving_tourist_trip_design_problems?utm_source=chatgpt.com))

**Trong hệ của bạn:** đây là hard constraints.

Nếu vi phạm Priority 0 → itinerary invalid.

## **Priority 1 — Đi hợp lý: tối ưu không gian và thứ tự**

Sau khi lịch “đúng”, bước tiếp theo là lịch phải **đi không ngu**.

| Yếu tố | Mục tiêu |
| ----- | ----- |
| Spatial efficiency | Gom điểm gần nhau cùng buổi/ngày |
| Ordering score | Thứ tự đi không vòng qua vòng lại |
| Travel time minimization | Giảm thời gian chết trên đường |
| Area clustering | Mỗi buổi nên tập trung một cụm khu vực |
| Start/end logic | Bắt đầu từ hotel/bến xe/sân bay, kết thúc hợp lý |

TripCraft cũng dùng **Spatial Score** và **Ordering Score** để đánh giá itinerary, tức là lịch tốt không chỉ đúng điểm, mà còn phải hợp lý về không gian và thứ tự. ([Hugging Face](https://huggingface.co/papers/2502.20508?utm_source=chatgpt.com))

**Trong hệ của bạn:** đây là phần OR-Tools / route optimizer.

Mục tiêu:  
giảm đi vòng \+ giảm thời gian di chuyển \+ gom điểm theo khu vực.

## **Priority 2 — Đúng gu user: cá nhân hóa**

Khi lịch đã khả thi và đi hợp lý, yếu tố tạo hài lòng mạnh nhất là **đúng sở thích**.

| Yếu tố | Ví dụ |
| ----- | ----- |
| Preference match | thích lịch sử, cafe, ăn chay, thiên nhiên |
| Persona fit | sinh viên, cặp đôi, gia đình, người lớn tuổi |
| Travel style | chill, khám phá, tiết kiệm, sang, local |
| Pace preference | đi nhanh, đi chậm, không muốn đi bộ nhiều |
| Food preference | ăn chay, bún bò, cafe muối, hải sản |
| Constraint mềm | tránh đông, thích chỗ ảnh đẹp, muốn ít tourist trap |

TRIP-PAL mô tả travel planning là tạo chuỗi hành động thỏa constraints và tối ưu tiêu chí hài lòng của user; họ dùng LLM để chuyển thông tin user thành data structure, rồi planner tạo plan đảm bảo constraint và tối ưu utility. ([arXiv](https://arxiv.org/abs/2406.10196?utm_source=chatgpt.com))

**Trong hệ của bạn:** đây là phần LLM extractor \+ tags \+ embedding \+ pgvector.

Không phải chọn POI rating cao nhất.  
Phải chọn POI hợp nhất với user này.

## **Priority 3 — Chất lượng điểm đến**

Đúng gu thôi chưa đủ. POI phải **đáng đi**.

| Yếu tố | Cách tính |
| ----- | ----- |
| Rating / review count | Chất lượng đại chúng |
| Popularity | Nơi đáng biết, biểu tượng địa phương |
| Local value | Có tính bản địa, không generic |
| Uniqueness | Khác biệt so với lịch trình bình thường |
| Reliability | Dữ liệu đủ chắc, không hallucinate |
| Cost-value ratio | Giá bỏ ra có xứng đáng không |

Với Huế, ví dụ: Đại Nội có priority cao vì giá trị văn hóa/lịch sử; cafe muối local có priority cao nếu user thích trải nghiệm bản địa; một quán rating thấp hoặc xa cụm di chuyển thì bị phạt.

POI Score \=  
  quality  
\+ popularity  
\+ local\_value  
\+ uniqueness  
\- cost\_penalty  
\- distance\_penalty

## **Priority 4 — Nhịp độ và sức người**

Đây là cái nhiều app bỏ qua, nhưng ảnh hưởng rất lớn đến cảm nhận thật.

| Yếu tố | Tác dụng |
| ----- | ----- |
| Không nhồi quá nhiều điểm | Tránh mệt và vỡ lịch |
| Có break | Cafe/nghỉ trưa/nghỉ chiều |
| Đúng giờ ăn | Không xếp ăn trưa lúc 15h |
| Tránh nắng/mưa nếu có data | Tăng comfort |
| Giảm walking nếu user yêu cầu | Rất quan trọng với gia đình/người lớn tuổi |
| Không đổi khu vực liên tục | Giảm cognitive load |

TripCraft có **Temporal Meal Score** và **Temporal Attraction Score**, tức là lịch tốt phải xếp ăn uống và điểm tham quan đúng thời điểm, không chỉ đúng địa điểm. ([Hugging Face](https://huggingface.co/papers/2502.20508?utm_source=chatgpt.com))

Một itinerary tốt không chỉ “đi được”.  
Nó phải “đi xong vẫn vui”.

## **Priority 5 — Đa dạng trải nghiệm**

Nếu lịch quá một màu, user dễ chán dù từng điểm đều tốt.

| Yếu tố | Ví dụ |
| ----- | ----- |
| Category balance | di tích \+ ăn uống \+ cafe \+ thiên nhiên \+ chợ |
| Intensity balance | sáng tham quan, chiều chill |
| Indoor/outdoor mix | tránh phụ thuộc thời tiết |
| Mainstream \+ hidden gems | vừa có biểu tượng, vừa có điểm mới |
| Food/culture/rest ratio | không chỉ chạy POI liên tục |

Ví dụ Huế 3 ngày mà toàn lăng/tẩm/chùa thì đúng nhưng dễ ngán. Lịch hay hơn là:

Ngày 1: nhập môn Huế \+ Đại Nội \+ cafe muối \+ sông Hương  
Ngày 2: lăng tẩm \+ chùa \+ ăn local  
Ngày 3: chợ \+ trải nghiệm nhẹ \+ mua quà \+ chill

## **Priority 6 — Cảm xúc và ký ức đáng nhớ**

Đây là tầng biến chuyến đi từ “hợp lý” thành “đáng nhớ”.

Tourism research có khái niệm **Memorable Tourism Experience**, gồm 7 domain: hedonism, refreshment, local culture, meaningfulness, knowledge, involvement và novelty. ([Sage Journals](https://journals.sagepub.com/doi/10.1177/0047287510385467?utm_source=chatgpt.com))

Dịch sang sản phẩm:

| Yếu tố | Nghĩa trong itinerary |
| ----- | ----- |
| Hedonism | vui, ngon, đẹp, sướng |
| Refreshment | có cảm giác nghỉ dưỡng, không kiệt sức |
| Local culture | có chất địa phương |
| Meaningfulness | có câu chuyện, ý nghĩa |
| Knowledge | học được lịch sử/văn hóa |
| Involvement | user được chọn/chỉnh theo gu |
| Novelty | có trải nghiệm mới, không đại trà |

Đây là chỗ bạn có thể vượt app planner thường: không chỉ tối ưu tuyến, mà còn tối ưu **trải nghiệm**.

## **Priority 7 — Narrative flow: lịch có câu chuyện**

Cái này không phải toán thuần, nhưng rất quan trọng khi trình bày itinerary.

Một lịch có narrative sẽ khiến user thấy chuyến đi “có ý đồ”:

Ngày 1: Làm quen với Huế cổ  
Ngày 2: Đi sâu vào văn hóa \- lịch sử  
Ngày 3: Sống chậm, ăn uống, mua quà, kết thúc nhẹ

Narrative giúp itinerary có cảm giác premium hơn hẳn lịch kiểu:

Day 1: Place A, Place B, Place C  
Day 2: Place D, Place E, Place F

## **Priority 8 — Linh hoạt và reroute**

Lịch trình thật luôn thay đổi: user dậy muộn, trời mưa, POI đóng cửa, mệt, muốn bỏ điểm.

Flex-TravelPlanner nhấn mạnh real-world planning cần thích nghi với yêu cầu thay đổi và cân bằng constraint cạnh tranh; các model hiện tại còn struggle khi constraints được thêm dần hoặc có mức ưu tiên khác nhau. ([arXiv](https://arxiv.org/abs/2506.04649?utm_source=chatgpt.com))

Với app của bạn, đây là feature ăn tiền:

Tôi trễ 1 tiếng → re-optimize  
Trời mưa → đổi outdoor sang indoor  
Tôi mệt → giảm POI, giữ điểm quan trọng  
Tôi muốn thêm cafe muối → chèn vào cụm gần nhất  
POI đóng cửa → thay bằng POI tương tự

## **Priority 9 — Giảm decision fatigue**

Travel planning không thiếu thông tin, mà thiếu **quyết định rõ ràng**. TravelPlanner benchmark cũng cho thấy travel planning phức tạp vì phải dùng tool, giữ nhiều constraint và tạo plan nhất quán; GPT-4 trong benchmark chỉ đạt 0.6% success rate. ([arXiv](https://arxiv.org/abs/2402.01622?utm_source=chatgpt.com))

Với user thường, app nên tránh đưa 50 lựa chọn. Nên đưa:

Best plan  
Alternative 1: tiết kiệm hơn  
Alternative 2: chill hơn  
Alternative 3: nhiều trải nghiệm hơn

User cần cảm giác: **“Ok, tôi tin lịch này đi được.”**

# **Bảng ưu tiên tổng hợp**

| Rank | Yếu tố | Loại | Mức ưu tiên |
| ----- | ----- | ----- | ----- |
| 0 | Feasibility: giờ mở cửa, travel time, daily time, budget, locked POI | Hard constraint | Bắt buộc |
| 1 | Spatial \+ ordering efficiency | Optimization | Rất cao |
| 2 | Preference/persona fit | Personalization | Rất cao |
| 3 | POI quality/local value | Recommendation | Cao |
| 4 | Comfort/fatigue/meal timing | Experience | Cao |
| 5 | Diversity/category balance | Experience | Trung-cao |
| 6 | Memorable experience: local culture, novelty, meaning | Emotional value | Trung-cao |
| 7 | Narrative flow | Presentation/UX | Trung bình |
| 8 | Robustness/reroute | Dynamic planning | Trung-cao nếu app mobile |
| 9 | Decision clarity | UX | Cao với consumer product |

# **Công thức score mình đề xuất cho hệ của bạn**

Trip Satisfaction Score \=  
  0.20 \* Feasibility Score  
\+ 0.15 \* Preference Match  
\+ 0.13 \* Spatial Efficiency  
\+ 0.12 \* POI Quality  
\+ 0.10 \* Comfort / Fatigue  
\+ 0.09 \* Budget Fit  
\+ 0.08 \* Diversity  
\+ 0.06 \* Localness / Novelty  
\+ 0.04 \* Narrative Flow  
\+ 0.03 \* Robustness

Nhưng khi implement, đừng để feasibility là soft score hoàn toàn. Nên chia:

Hard Constraints:  
\- Không đi ngoài giờ mở cửa  
\- Không vượt daily time limit  
\- Không vượt budget nghiêm trọng  
\- Locked POIs phải được giữ  
\- Travel time phải khả thi  
\- Có meal/rest slots cơ bản

Soft Objectives:  
\- Max preference match  
\- Max POI quality  
\- Max localness  
\- Max diversity  
\- Min travel time  
\- Min walking/fatigue  
\- Min cost penalty  
\- Min waiting time

# **Chốt ngắn gọn cho đề tài**

Thứ tự ưu tiên đúng nhất là:

1\. Lịch phải khả thi  
2\. Đường đi phải hợp lý  
3\. Điểm đến phải đúng gu user  
4\. Điểm đến phải chất lượng  
5\. Nhịp độ phải thoải mái  
6\. Trải nghiệm phải đa dạng  
7\. Phải có chất địa phương / mới lạ / đáng nhớ  
8\. Lịch phải có câu chuyện  
9\. Phải reroute được khi thực tế thay đổi  
10\. Phải giảm gánh nặng quyết định cho user

Câu pitch rất mạnh:

Hệ thống tối ưu trải nghiệm du lịch theo thứ tự ưu tiên: trước hết đảm bảo lịch trình khả thi, sau đó tối ưu tuyến đường, cá nhân hóa theo sở thích, chọn POI chất lượng, cân bằng sức người/ngân sách/thời gian, và cuối cùng tạo một hành trình có tính bản địa, đa dạng, đáng nhớ và có thể tự điều chỉnh khi điều kiện thay đổi.

