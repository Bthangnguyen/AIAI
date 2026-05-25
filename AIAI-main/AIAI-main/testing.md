Được. Đây là **100 testcases prompt-level** để test full pipeline: Layer 2 hiểu ý user, Layer 3 chọn POI đúng gu, Layer 4 sắp lịch hợp lý, validator/narrative xử lý mâu thuẫn.

Bạn không cần kỳ vọng output giống nhau 100%, mà chấm theo các điểm:

1\. Extract đúng: budget, days, tags, locked POIs, pace, food, avoid, persona  
2\. Candidate đúng: POI hợp gu, không hallucinate, có food/cafe/rest phù hợp  
3\. Solver đúng: không vượt thời gian, không đi vòng, không quá mệt  
4\. Conflict handling: biết hỏi lại hoặc ưu tiên constraint quan trọng  
5\. Narrative: kể đúng theo sequence thật, không bịa điểm

---

# **100 testcases đa dạng cho AI Travel Optimizer**

## **A. Basic itinerary — test hiểu ý cơ bản**

| ID | Prompt user | Cần kiểm tra |
| ----- | ----- | ----- |
| T001 | “Tôi muốn đi Huế 1 ngày, ngân sách 500k, thích Đại Nội và ăn bún bò.” | num\_days=1, budget, locked Đại Nội, food=bún bò |
| T002 | “Lên lịch Huế 2 ngày cho sinh viên, rẻ, đi được nhiều điểm nổi tiếng.” | budget thấp, pace hơi nhanh, iconic POIs |
| T003 | “Tôi đi Huế 3 ngày, muốn lịch nhẹ nhàng, không cần quá nhiều điểm.” | pace=chill, max POI/day thấp |
| T004 | “Tôi có 1 buổi chiều ở Huế, muốn đi chỗ đẹp và ăn món local.” | time\_slot=afternoon, duration ngắn |
| T005 | “Tôi muốn lịch trình Huế 4 ngày, cân bằng giữa di tích, đồ ăn và cafe.” | diversity target balanced |
| T006 | “Tôi đến Huế lần đầu, hãy cho tôi lịch trình must-visit 2 ngày.” | first\_time=true, iconic priority cao |
| T007 | “Tôi từng đi Đại Nội rồi, lần này muốn lịch khác lạ hơn.” | avoid/visited Đại Nội, novelty cao |
| T008 | “Tôi muốn đi Huế cuối tuần, 2 ngày 1 đêm, lịch vừa phải.” | 2 ngày, balanced pace |
| T009 | “Tôi chỉ muốn đi quanh trung tâm Huế, đừng xếp điểm quá xa.” | radius nhỏ, spatial penalty cao |
| T010 | “Tôi muốn đi Huế 5 ngày, có cả tham quan, ăn uống, nghỉ ngơi.” | multi-day, diversity \+ rest |

---

## **B. Sở thích sâu / persona**

| ID | Prompt user | Cần kiểm tra |
| ----- | ----- | ----- |
| T011 | “Tôi thích lịch sử triều Nguyễn, hãy ưu tiên các điểm có giá trị văn hóa.” | culture/history weight cao |
| T012 | “Tôi thích sống ảo, chỗ nào chụp ảnh đẹp thì ưu tiên.” | photo\_spot tag, scenic POIs |
| T013 | “Tôi thích chỗ local, ít khách du lịch, không quá thương mại.” | localness cao, tourist\_trap penalty |
| T014 | “Tôi đi với bạn gái, muốn lịch lãng mạn, nhẹ nhàng, có cafe đẹp.” | persona=couple, vibe=romantic |
| T015 | “Tôi đi với gia đình có trẻ nhỏ, tránh lịch quá dày.” | family/kids, comfort cao |
| T016 | “Tôi đi với ba mẹ lớn tuổi, hạn chế đi bộ và leo dốc.” | walking\_tolerance=low, accessibility |
| T017 | “Tôi đi một mình, thích khám phá, có thể đi nhiều điểm.” | solo, pace=intense |
| T018 | “Tôi muốn chuyến đi kiểu healing, chậm, nhiều không gian yên tĩnh.” | vibe=healing/chill, rest/nature |
| T019 | “Tôi muốn trải nghiệm Huế cổ, trầm, có chiều sâu văn hóa.” | narrative/culture/local |
| T020 | “Tôi thích thiên nhiên hơn di tích, nhưng vẫn muốn ghé Đại Nội.” | nature weight cao \+ locked Đại Nội |

---

## **C. Food preference / meal timing**

| ID | Prompt user | Cần kiểm tra |
| ----- | ----- | ----- |
| T021 | “Tôi ăn chay, đi Huế 2 ngày, nhớ xếp quán chay vào bữa trưa.” | vegetarian, lunch window |
| T022 | “Tôi muốn ăn bún bò, chè Huế, cafe muối trong lịch 1 ngày.” | food locked/desired, meal slots |
| T023 | “Tôi không ăn cay, tránh món quá cay.” | avoid spicy |
| T024 | “Tôi muốn food tour Huế buổi tối, khoảng 4 tiếng.” | trip\_type=food\_tour, evening |
| T025 | “Tôi thích cafe hopping, muốn đi 3 quán cafe khác nhau trong 1 ngày.” | cafe\_hopping, diversity category không ép quá mạnh |
| T026 | “Tôi muốn ăn local nhưng ngân sách ăn uống dưới 200k/ngày.” | food budget constraint |
| T027 | “Tôi ăn chay nhưng bạn tôi muốn thử bún bò, hãy cân bằng.” | group conflict food |
| T028 | “Tôi muốn lịch có bữa trưa rõ ràng, đừng để ăn trưa quá muộn.” | meal timing score |
| T029 | “Tôi muốn ăn đặc sản Huế nhưng không muốn vào quán quá đông.” | local food \+ avoid crowded |
| T030 | “Tôi chỉ có buổi sáng, muốn cafe muối và một điểm tham quan gần đó.” | morning, cafe \+ nearby POI |

---

## **D. Pace / comfort / fatigue**

| ID | Prompt user | Cần kiểm tra |
| ----- | ----- | ----- |
| T031 | “Tôi không muốn đi bộ nhiều, ưu tiên các điểm gần nhau.” | walking low, cluster |
| T032 | “Tôi muốn đi thật nhiều điểm trong 1 ngày, càng dày càng tốt.” | pace=intense, nhưng vẫn feasible |
| T033 | “Tôi dễ mệt, cứ 2 tiếng nên có nghỉ.” | rest\_interval |
| T034 | “Tránh xếp điểm ngoài trời vào buổi trưa vì Huế nắng.” | outdoor avoidance 12–14 |
| T035 | “Tôi muốn lịch nhẹ, mỗi ngày tối đa 4 điểm.” | max\_pois\_per\_day=4 |
| T036 | “Tôi muốn lịch trekking/đi bộ nhiều cũng được, miễn đẹp.” | walking tolerance high |
| T037 | “Tôi chỉ muốn đi buổi sáng, chiều nghỉ ở khách sạn.” | time\_window morning |
| T038 | “Ngày đầu tôi đến muộn lúc 14h, chỉ plan từ chiều trở đi.” | day 1 start time |
| T039 | “Ngày cuối tôi phải ra ga lúc 16h, đừng xếp điểm xa sau 14h.” | end constraint |
| T040 | “Tôi muốn mỗi ngày có ít nhất một khoảng chill/cafe break.” | rest/cafe slot |

---

## **E. Budget / cost conflict**

| ID | Prompt user | Cần kiểm tra |
| ----- | ----- | ----- |
| T041 | “Tôi có 300k cho 2 ngày ở Huế, muốn đi nhiều điểm nhất có thể.” | budget conflict, free/cheap POI |
| T042 | “Ngân sách 2 triệu, tôi muốn lịch thoải mái, có quán ngon.” | budget medium, quality food |
| T043 | “Tôi muốn tiết kiệm tối đa, ưu tiên điểm miễn phí.” | free POI priority |
| T044 | “Tôi không quan tâm giá, miễn trải nghiệm tốt nhất.” | budget low weight |
| T045 | “Tôi muốn đi Đại Nội, lăng Khải Định, lăng Minh Mạng nhưng chỉ có 200k.” | budget conflict with entrance fees |
| T046 | “Tôi muốn lịch sang hơn một chút, cafe đẹp, nhà hàng ổn.” | premium preference |
| T047 | “Tôi đi nhóm 4 người, ngân sách tổng 2 triệu.” | group budget normalization |
| T048 | “Tôi có 1 triệu cho 3 ngày, chủ yếu đi ăn và cafe local.” | budget tight, food/cafe |
| T049 | “Nếu vượt ngân sách nhẹ cũng được, nhưng đừng quá 20%.” | soft budget |
| T050 | “Tôi muốn app giải thích vì sao lịch này hợp ngân sách.” | explanation budget |

---

## **F. Locked POIs / avoid POIs / visited POIs**

| ID | Prompt user | Cần kiểm tra |
| ----- | ----- | ----- |
| T051 | “Bắt buộc có Đại Nội và chùa Thiên Mụ trong ngày đầu.” | locked POIs day 1 |
| T052 | “Tôi không muốn đi lăng tẩm, hãy tránh các lăng.” | avoid category tomb |
| T053 | “Tôi đã đi chợ Đông Ba rồi, đừng xếp lại.” | visited POI exclusion |
| T054 | “Tôi muốn đi Đại Nội nhưng không muốn đi các điểm quá đông.” | conflict: iconic vs crowded |
| T055 | “Bắt buộc có cafe muối, còn lại tùy bạn.” | locked food/cafe |
| T056 | “Tôi muốn đi các lăng nhưng chỉ chọn 1 lăng đẹp nhất thôi.” | category cap tomb=1 |
| T057 | “Tôi muốn có sông Hương trong lịch, nhưng không cần du thuyền.” | semantic locked area/activity |
| T058 | “Tôi muốn đi Thiên Mụ lúc hoàng hôn nếu hợp tuyến.” | preferred time slot |
| T059 | “Đừng xếp điểm mua sắm, tôi không thích shopping.” | avoid shopping |
| T060 | “Tôi muốn giữ Đại Nội, còn nếu quá tải thì bỏ các điểm khác.” | locked priority |

---

## **G. Mâu thuẫn / ambiguity / robustness**

| ID | Prompt user | Cần kiểm tra |
| ----- | ----- | ----- |
| T061 | “Tôi muốn đi thật nhiều điểm nhưng lịch phải thật chill.” | conflict pace |
| T062 | “Ngân sách 200k nhưng muốn ăn nhà hàng ngon và đi nhiều điểm có vé.” | budget conflict |
| T063 | “Tôi muốn đi Huế 1 ngày nhưng phải có Đại Nội, 3 lăng, chợ, cafe, ăn tối.” | overpacked day |
| T064 | “Tôi không thích di tích nhưng bắt buộc phải đi Đại Nội.” | negative preference \+ locked |
| T065 | “Tôi muốn đi ngoài trời nhưng tránh nắng và mưa.” | weather conflict |
| T066 | “Tôi muốn lịch local nhưng cũng phải có các điểm nổi tiếng nhất.” | local vs iconic balance |
| T067 | “Tôi muốn đi 2 ngày, nhưng ngày đầu chỉ rảnh 2 tiếng.” | uneven day availability |
| T068 | “Tôi thích ăn chay, nhưng muốn thử đặc sản Huế truyền thống.” | food conflict |
| T069 | “Tôi muốn lịch tiết kiệm nhưng không muốn đi bộ nhiều.” | budget vs transport |
| T070 | “Tôi muốn đi xa trung tâm nhưng chỉ có buổi chiều.” | distance/time conflict |

---

## **H. Narrative / story / emotional flow**

| ID | Prompt user | Cần kiểm tra |
| ----- | ----- | ----- |
| T071 | “Hãy tạo lịch Huế 3 ngày có câu chuyện: ngày 1 làm quen, ngày 2 khám phá sâu, ngày 3 chill.” | narrative flow |
| T072 | “Tôi muốn chuyến đi mang cảm giác hoài cổ và chậm rãi.” | vibe narrative |
| T073 | “Tôi muốn lịch như một hành trình tìm hiểu văn hóa Huế.” | story culture |
| T074 | “Tôi muốn mỗi ngày có một chủ đề riêng.” | day theme generation |
| T075 | “Tôi muốn lịch cho cặp đôi, lãng mạn nhưng không sến.” | tone control |
| T076 | “Tôi muốn lịch kiểu food story, đi từ món sáng đến món tối.” | food narrative |
| T077 | “Tôi muốn một chuyến đi chữa lành, ít điểm nhưng có ý nghĩa.” | meaningfulness \+ refreshment |
| T078 | “Tôi muốn lịch có đoạn kết đẹp ở sông Hương hoặc cafe chiều.” | end-of-trip narrative |
| T079 | “Tôi muốn khám phá Huế như người địa phương.” | local narrative |
| T080 | “Viết lịch đừng khô, hãy giải thích vì sao xếp như vậy.” | explanation quality |

---

## **I. Multi-plan / alternatives**

| ID | Prompt user | Cần kiểm tra |
| ----- | ----- | ----- |
| T081 | “Cho tôi 3 phương án: tiết kiệm, cân bằng, chill.” | multi-plan |
| T082 | “Tôi muốn bản lịch chính và một bản ít đi bộ hơn.” | alternative comfort |
| T083 | “Tạo một lịch nhiều di tích và một lịch nhiều đồ ăn.” | different weight profiles |
| T084 | “Cho tôi bản lịch nếu trời mưa và bản nếu trời đẹp.” | weather alternatives |
| T085 | “Tôi muốn so sánh lịch nhanh-gọn với lịch thư thả.” | pace alternatives |
| T086 | “Tạo lịch cho người lần đầu đến Huế và một bản hidden gems.” | iconic vs novelty |
| T087 | “Tôi muốn một phương án không vượt 500k và một phương án trải nghiệm tốt nhất.” | budget vs premium |
| T088 | “Cho tôi 2 lịch khác nhau nhưng đều giữ Đại Nội.” | overlap control with locked |
| T089 | “Tôi muốn 3 plan nhưng đừng giống nhau quá.” | Jaccard overlap check |
| T090 | “Tôi muốn bản local food, bản cultural, bản romantic.” | style configs |

---

## **J. Reroute / dynamic update**

| ID | Prompt user | Cần kiểm tra |
| ----- | ----- | ----- |
| T091 | “Tôi trễ 1 tiếng so với lịch, hãy tối ưu lại phần còn lại.” | reroute late |
| T092 | “Tôi mệt rồi, bỏ bớt điểm nhưng giữ Đại Nội.” | fatigue reroute |
| T093 | “Trời mưa, đổi các điểm ngoài trời sang trong nhà.” | weather reroute |
| T094 | “Quán ăn trong lịch đóng cửa, đổi sang quán gần đó cùng kiểu.” | replacement same category |
| T095 | “Tôi muốn thêm cafe muối vào lịch hiện tại.” | insert new POI |
| T096 | “Tôi muốn bỏ lăng Khải Định, hãy sắp lại cho hợp lý.” | remove POI \+ reoptimize |
| T097 | “Tôi đang ở chợ Đông Ba, hãy reroute từ vị trí hiện tại.” | current location start |
| T098 | “Tôi chỉ còn 3 tiếng, chọn phần đáng đi nhất trong lịch.” | utility-based pruning |
| T099 | “Tôi muốn đổi lịch ngày 2 thành nhẹ nhàng hơn.” | partial day reroute |
| T100 | “Tôi muốn giữ các điểm ăn uống, bỏ bớt điểm tham quan nếu thiếu thời gian.” | priority override |

---

# **Format JSONL mẫu để đưa vào test pipeline**

Ví dụ bạn có thể convert mỗi case thành dạng này:

{  
  "id": "T021",  
  "user\_prompt": "Tôi ăn chay, đi Huế 2 ngày, nhớ xếp quán chay vào bữa trưa.",  
  "expected": {  
    "num\_days": 2,  
    "food\_preferences": \["vegetarian"\],  
    "meal\_constraints": \["lunch\_required"\],  
    "pace": "balanced"  
  },  
  "checks": \[  
    "Layer 2 extract vegetarian correctly",  
    "Layer 3 includes vegetarian restaurant candidates",  
    "Layer 4 schedules lunch within lunch window",  
    "Validator meal\_timing\_score \>= 0.8"  
  \]  
}

# **Bộ tiêu chí chấm mỗi testcase**

Mỗi testcase nên chấm 0–5 theo 6 mục:

Intent Understanding        /5  
Preference Matching         /5  
Constraint Satisfaction     /5  
Spatial/Temporal Quality    /5  
Comfort & Diversity         /5  
Narrative/Explanation       /5

Tổng:

\>= 26/30: rất tốt  
22–25: ổn  
18–21: cần cải thiện  
\<18: fail pipeline

