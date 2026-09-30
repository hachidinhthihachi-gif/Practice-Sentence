"""
Luyện dịch Việt -> Anh: BẮT BUỘC dùng phrasal verb / collocation / idiom cho sẵn.
- Chấm ngữ pháp (LanguageTool, miễn phí), tô xanh = đúng, đỏ = sai, có điểm /10
- Dưới bài chấm có gợi ý câu tự nhiên hơn
- CHỈ được sang câu khác khi đạt 10/10

Không cần cài thư viện (chỉ dùng thư viện có sẵn của Python).
Chạy:   python phrase_drill.py      rồi mở  http://localhost:8002

Thêm câu của riêng bạn: tạo file bank.txt cùng thư mục, mỗi dòng 1 câu, cách nhau bằng dấu |
    loại|cụm bắt buộc|nghĩa tiếng Việt|câu tiếng Việt|câu tiếng Anh tự nhiên
    loại là: pv (phrasal verb), col (collocation) hoặc idiom
    ví dụ:  pv|look up to|ngưỡng mộ|Tôi rất ngưỡng mộ cô giáo của mình.|I really look up to my teacher.
    (tuỳ chọn) thêm 4 trường diễn giải cuối dòng: |nghĩa từng từ|vì sao gộp lại ra nghĩa này|nguồn gốc|ngữ cảnh dùng
Nếu dịch lời giải thích lỗi bị 429 trên Render: đặt biến môi trường MYMEMORY_EMAIL=<email của bạn>.
"""
import argparse
import json
import os
import re
import socket
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode, urlparse

# loại|cụm bắt buộc|nghĩa|câu Việt|câu Anh tự nhiên
BANK_TEXT = """
pv|look forward to|mong chờ|Tôi rất mong chờ chuyến đi chơi cuối tuần này.|I'm really looking forward to this weekend's trip.
pv|give up|từ bỏ, bỏ cuộc|Đừng bỏ cuộc, bạn sắp thành công rồi.|Don't give up; you're almost there.
pv|figure out|tìm ra, hiểu ra|Tôi vẫn chưa tìm ra cách sửa chiếc máy này.|I still can't figure out how to fix this machine.
pv|run out of|hết, cạn kiệt|Nhà mình hết sữa rồi, bạn mua thêm được không?|We've run out of milk. Can you buy some more?
pv|put off|trì hoãn|Anh ấy cứ trì hoãn việc đi khám bác sĩ.|He keeps putting off going to the doctor.
pv|turn down|từ chối|Cô ấy từ chối lời mời làm việc vì mức lương quá thấp.|She turned down the job offer because the salary was too low.
pv|get along with|hòa thuận với|Tôi hòa thuận với tất cả đồng nghiệp của mình.|I get along with all my colleagues.
pv|carry out|thực hiện, tiến hành|Nhóm nghiên cứu sẽ tiến hành thí nghiệm vào tuần tới.|The research team will carry out the experiment next week.
pv|come across|tình cờ gặp, tình cờ thấy|Hôm qua tôi tình cờ thấy bức ảnh cũ của chúng ta.|I came across our old photo yesterday.
pv|take over|tiếp quản|Con trai ông ấy sẽ tiếp quản công ty vào năm sau.|His son will take over the company next year.
pv|break down|hỏng, hỏng máy|Xe của tôi bị hỏng giữa đường.|My car broke down in the middle of the road.
pv|set up|thành lập, thiết lập|Họ đã thành lập công ty riêng vào năm ngoái.|They set up their own company last year.
pv|find out|tìm ra, biết được|Tôi vừa biết được là cô ấy sắp chuyển nhà.|I just found out that she is moving.
pv|call off|hủy bỏ|Trận đấu bị hủy vì thời tiết xấu.|The match was called off because of the bad weather.
pv|bring up|nuôi dưỡng; nêu ra|Bà tôi đã một mình nuôi tôi khôn lớn.|My grandmother brought me up on her own.
pv|get over|vượt qua, hồi phục sau|Anh ấy vẫn chưa vượt qua được nỗi buồn khi mất việc.|He still hasn't gotten over losing his job.
col|make a decision|đưa ra quyết định|Bạn cần đưa ra quyết định trước thứ Sáu.|You need to make a decision by Friday.
col|heavy rain|mưa lớn|Mưa lớn đã làm ngập nhiều con đường.|Heavy rain flooded many roads.
col|take a break|nghỉ giải lao|Chúng ta nghỉ giải lao mười phút nhé.|Let's take a break for ten minutes.
col|do homework|làm bài tập về nhà|Con phải làm bài tập về nhà trước khi xem tivi.|You have to do your homework before you watch TV.
col|pay attention to|chú ý đến|Hãy chú ý đến những chi tiết nhỏ.|Please pay attention to the small details.
col|strong coffee|cà phê đậm|Tôi cần một tách cà phê đậm để tỉnh táo.|I need a cup of strong coffee to stay awake.
col|catch a cold|bị cảm|Hôm qua tôi đi dưới mưa nên bị cảm.|I caught a cold because I walked in the rain yesterday.
col|keep a promise|giữ lời hứa|Anh ấy luôn giữ lời hứa với các con.|He always keeps his promises to his children.
col|break the law|vi phạm pháp luật|Vừa uống rượu vừa lái xe là vi phạm pháp luật.|Drinking and driving breaks the law.
col|make progress|tiến bộ|Em bé đã tiến bộ rất nhiều trong việc tập đọc.|The child has made great progress in learning to read.
col|save money|tiết kiệm tiền|Tôi đang tiết kiệm tiền để mua một chiếc xe máy.|I'm saving money to buy a motorbike.
col|take a look at|xem qua|Bạn xem qua bản báo cáo này giúp tôi được không?|Could you take a look at this report for me?
col|fast food|đồ ăn nhanh|Ăn quá nhiều đồ ăn nhanh không tốt cho sức khỏe.|Eating too much fast food is bad for your health.
col|have a good/great time|có khoảng thời gian vui vẻ|Tối qua chúng tôi đã có khoảng thời gian rất vui ở nhà bạn.|We had a really good time at your house last night.
col|reach a conclusion|đi đến kết luận|Sau nhiều cuộc họp, họ vẫn chưa đi đến kết luận nào.|After many meetings, they still haven't reached a conclusion.
col|meet the deadline|kịp thời hạn|Chúng tôi phải làm việc suốt đêm để kịp thời hạn.|We had to work all night to meet the deadline.
idiom|break the ice|phá vỡ sự ngượng ngùng ban đầu|Anh ấy kể một câu chuyện cười để phá vỡ bầu không khí ngượng ngùng lúc đầu.|He told a joke to break the ice.
idiom|a piece of cake|dễ như ăn bánh|Bài kiểm tra hôm nay dễ như ăn bánh.|Today's test was a piece of cake.
idiom|once in a blue moon|rất hiếm khi|Anh ấy rất hiếm khi mới ghé thăm chúng tôi.|He only visits us once in a blue moon.
idiom|under the weather|không khỏe|Hôm nay tôi thấy trong người không khỏe nên ở nhà.|I'm feeling under the weather today, so I'm staying home.
idiom|cost an arm and a leg|rất đắt đỏ|Chiếc điện thoại mới này đắt cắt cổ.|This new phone cost an arm and a leg.
idiom|hit the books|học bài chăm chỉ|Sắp thi rồi nên tôi phải chăm chỉ học bài.|I have to hit the books because the exams are coming up.
idiom|spill the beans|tiết lộ bí mật|Ai đó đã lỡ tiết lộ bí mật về bữa tiệc bất ngờ.|Somebody spilled the beans about the surprise party.
idiom|the ball is in one's court|đến lượt ai đó quyết định|Tôi đã đưa ra đề nghị rồi, giờ đến lượt bạn quyết định.|I've made my offer, so the ball is in your court now.
idiom|kill two birds with one stone|một mũi tên trúng hai đích|Đạp xe đi làm giúp tôi vừa tiết kiệm tiền vừa tập thể dục, đúng là một mũi tên trúng hai đích.|By cycling to work, I kill two birds with one stone: I save money and get exercise.
idiom|bite the bullet|cắn răng chịu đựng|Tôi phải cắn răng chịu đựng và đi nhổ chiếc răng đau.|I had to bite the bullet and get my tooth pulled.
idiom|on the same page|cùng quan điểm, hiểu nhau|Trước khi bắt đầu, chúng ta cần chắc chắn mọi người đều cùng quan điểm.|Before we start, we need to make sure everyone is on the same page.
idiom|call it a day|kết thúc công việc hôm nay|Chúng ta làm đủ rồi, hôm nay nghỉ thôi.|We've done enough; let's call it a day.
idiom|beat around the bush|nói vòng vo|Đừng nói vòng vo nữa, hãy nói thẳng vào vấn đề.|Stop beating around the bush and get to the point.
idiom|hit the nail on the head|nói trúng phóc|Bạn nói trúng phóc vấn đề rồi.|You hit the nail on the head.
idiom|get out of hand|vượt khỏi tầm kiểm soát|Bữa tiệc dần vượt khỏi tầm kiểm soát nên cảnh sát phải đến.|The party got out of hand, so the police had to come.
idiom|in the same boat|cùng chung cảnh ngộ|Đừng lo, tất cả chúng ta đều cùng chung cảnh ngộ.|Don't worry; we're all in the same boat.
"""



# cụm|nghĩa từng từ|vì sao gộp lại ra nghĩa này|nguồn gốc / cách hình thành|ngữ cảnh dùng
EXPLAIN_TEXT = """
look forward to|look = nhìn; forward = về phía trước; to = tới, hướng tới|Nhìn về phía trước, hướng tới điều sắp xảy ra nên có nghĩa mong chờ, háo hức.|Ẩn dụ đơn giản: mắt hướng về tương lai. Chú ý "to" ở đây là giới từ nên theo sau là danh từ hoặc V-ing (looking forward to seeing you).|Dùng cả thân mật lẫn trang trọng, rất hay gặp ở cuối thư/email: I look forward to hearing from you.
give up|give = đưa, trao; up = lên, hết|"Trao đi" nỗ lực hoặc thói quen, còn "up" nhấn mạnh sự trọn vẹn nên nghĩa là bỏ hẳn.|Hạt từ "up" trong nhiều phrasal verb chỉ sự hoàn tất (eat up, use up, give up). Đây là cách hình thành nghĩa, không phải một điển tích.|Rất thông dụng: bỏ cuộc, bỏ thói quen (give up smoking). Sau give up dùng V-ing hoặc danh từ.
figure out|figure = con số, hình dạng, phép tính; out = ra ngoài|Tính toán, cân nhắc cho đến khi lời giải "lộ ra" nên có nghĩa tìm ra, hiểu ra.|"Figure" gốc gần với "figures" (các con số, tính toán); "out" gợi điều ẩn giấu được đưa ra ánh sáng.|Dùng khi giải quyết vấn đề hoặc hiểu ai đó, cái gì đó: figure out how to..., figure out why.... Thân mật đến trung tính.
run out of|run = chạy, chảy; out of = ra khỏi|Nguồn cung "chảy/chạy ra khỏi" mình nên hết sạch.|Hình ảnh chất lỏng chảy cạn khỏi bình; "run" có nghĩa gốc là chảy, giống nước chảy đi hết.|Dùng khi hết đồ dùng, thời gian, kiên nhẫn: run out of milk/time/patience. Sau "of" là danh từ.
put off|put = đặt; off = rời ra, xa ra|"Đặt" việc ra xa khỏi thời điểm hiện tại nên nghĩa là trì hoãn.|Hạt từ "off" chỉ sự tách rời, đẩy ra xa. Cách hình thành nghĩa, không có điển tích riêng.|Dùng khi hoãn việc (put off + V-ing/danh từ), thân mật lẫn trang trọng. Lưu ý put off đôi khi còn nghĩa "làm mất hứng" tùy ngữ cảnh.
turn down|turn = xoay, vặn; down = xuống|Nghĩa gốc là vặn nhỏ xuống (turn down the volume); nghĩa mở rộng là "hạ" một lời đề nghị xuống, tức từ chối.|Từ nghĩa vật lý (vặn nhỏ) chuyển sang nghĩa bóng (bác bỏ đề nghị).|Dùng khi từ chối lời mời, lời đề nghị, ứng viên: turn down an offer. Lịch sự và thông dụng.
get along with|get = trở nên, đi; along = cùng nhau, song song; with = với|"Đi cùng nhau" suôn sẻ với ai đó nên nghĩa là hòa thuận.|"Along" gợi hình ảnh hai người cùng đi trên một con đường mà không va chạm.|Nói về quan hệ tốt với đồng nghiệp, bạn bè, hàng xóm. Thân mật. Tiếng Anh Anh hay dùng get on with.
carry out|carry = mang; out = ra ngoài|"Mang ra" kế hoạch từ trên giấy ra ngoài đời nên nghĩa là thực hiện, tiến hành.|Hình ảnh đem ý tưởng ra khỏi giai đoạn dự định để làm thật.|Hơi trang trọng: carry out research/an experiment/a plan/orders. Hay gặp trong công việc, khoa học.
come across|come = đến; across = băng ngang qua|Đi ngang qua và bắt gặp nên nghĩa là tình cờ gặp hoặc thấy.|"Across" gợi ý băng ngang lối đi nên tình cờ chạm mặt điều gì đó.|Dùng khi tình cờ tìm thấy vật hoặc gặp người. Còn nghĩa khác: come across as friendly = tạo ấn tượng thân thiện.
take over|take = lấy, nắm; over = sang, chuyển qua|Nắm lấy quyền điều khiển và "chuyển sang" mình nên nghĩa là tiếp quản.|"Over" chỉ sự chuyển giao từ người này sang người khác.|Dùng cho tiếp quản công ty, công việc, quyền điều hành; xuất hiện nhiều trong kinh doanh và tin tức.
break down|break = vỡ, gãy; down = xuống, dừng lại|Máy móc vỡ hoặc gãy rồi dừng lại nên nghĩa là hỏng, ngừng hoạt động.|"Down" gợi sự sụp đổ, ngừng lại. Nghĩa mở rộng: người suy sụp (break down in tears) hoặc chia nhỏ số liệu (break down the costs).|Dùng cho xe cộ, máy móc hỏng; cũng dùng cho tinh thần suy sụp hoặc phân tích chi tiết.
set up|set = đặt, sắp xếp; up = lên, dựng lên|Đặt và dựng lên một thứ cho hoạt động được nên nghĩa là thành lập, thiết lập.|"Up" gợi sự dựng lên. Cách hình thành nghĩa, không có điển tích.|Rất thông dụng: lập công ty, cài đặt thiết bị, sắp xếp cuộc hẹn (set up a meeting).
find out|find = tìm thấy; out = ra ngoài, lộ ra|Tìm cho đến khi sự thật "lộ ra" nên nghĩa là phát hiện, biết được thông tin.|Khác "find" (tìm thấy một vật cụ thể): find out là tìm ra thông tin hoặc sự thật.|Dùng khi biết được điều mới: find out about..., find out that..., find out who/why....
call off|call = gọi, tuyên bố; off = tắt, rời khỏi|"Tuyên bố" dừng một việc đã sắp xếp nên nghĩa là hủy bỏ.|"Off" chỉ sự cắt đứt, dừng lại; "call" mang nghĩa tuyên bố, ra lệnh.|Dùng cho hủy sự kiện, cuộc họp, trận đấu, kế hoạch.
bring up|bring = mang, đem; up = lên|Có hai nghĩa: "đưa lên" cho lớn dần (nuôi dạy) hoặc "đưa" một chủ đề lên để bàn.|Cả hai nghĩa cùng gợi hình ảnh nâng lên: nâng đứa trẻ lớn lên, nâng vấn đề lên mặt bàn.|Nuôi dạy: brought up by his grandparents. Nêu vấn đề: bring up a topic. Tân ngữ có thể chen giữa: bring her up.
get over|get = đạt tới, trở nên; over = vượt qua|Vượt qua như bước qua chướng ngại nên nghĩa là vượt qua, hồi phục sau.|"Over" gợi sự vượt qua một vật cản; ở đây vật cản là nỗi buồn hoặc bệnh tật.|Dùng cho nỗi buồn, chia tay, ốm bệnh: get over a cold/a breakup/the shock.
make a decision|make = làm, tạo ra; decision = quyết định|Người Anh coi quyết định là thứ được "tạo ra" nên dùng make, không nói "do a decision".|Collocation cố định theo thói quen của người bản xứ, không có điển tích riêng. Cùng kiểu: make a choice, make a plan.|Rất thông dụng ở mọi ngữ cảnh: make a decision about/on... Trang trọng hơn: reach a decision.
heavy rain|heavy = nặng; rain = mưa|"Nặng" ở đây nghĩa là dày, dữ dội (mưa nặng hạt). Thường không nói "big rain".|Collocation: heavy đi với rain, snow, traffic, smoker... Chỉ là thói quen kết hợp từ.|Dùng nhiều trong dự báo thời tiết và tin tức: heavy rain warning. Mạnh hơn nữa: torrential rain.
take a break|take = lấy; break = giờ nghỉ|"Lấy" một khoảng nghỉ cho bản thân. Không dùng "make a break" với nghĩa này.|Collocation cố định; take + danh từ hành động (take a rest/a walk/a break) tạo cách nói tự nhiên.|Thân mật, phổ biến ở công sở và trường học: coffee break, take a short break. Tiếng Anh Anh cũng hay nói have a break.
do homework|do = làm; homework = bài tập về nhà|Với bài tập, việc nhà, việc vặt người Anh dùng "do" (do the dishes, do homework), không dùng "make".|"Do" dùng cho công việc, nhiệm vụ nói chung; "make" thiên về tạo ra một vật hoặc kết quả.|Rất thông dụng với học sinh: do (one's) homework. Cũng nói do exercises, do research.
pay attention to|pay = trả; attention = sự chú ý; to = tới|Sự chú ý được xem như thứ có giá trị, bạn "trả" nó cho ai hoặc cái gì.|Ẩn dụ tiền bạc: chú ý như một loại "tiền" bạn bỏ ra. Chú ý "to" là giới từ nên theo sau là danh từ hoặc V-ing.|Trung tính, dùng khi nhắc nhở hoặc hướng dẫn: pay attention to details/the teacher. Cũng: pay attention in class.
strong coffee|strong = mạnh, đậm; coffee = cà phê|Với đồ uống, "strong" chỉ độ đậm. Không nói "heavy coffee".|Collocation: strong đi với coffee, tea, wind, smell, accent... Chỉ là thói quen kết hợp từ.|Dùng ở quán cà phê hoặc khi nói chuyện hằng ngày. Trái nghĩa: weak coffee/tea.
catch a cold|catch = bắt, nhiễm; a cold = bệnh cảm|Bệnh được xem như thứ "bắt" lấy từ môi trường hoặc từ người khác, giống bắt một quả bóng.|Collocation cố định, không nói "take a cold". Cùng kiểu: catch the flu, catch a virus.|Dùng hằng ngày. Khi đã bị cảm rồi thì nói have a cold.
keep a promise|keep = giữ; promise = lời hứa|Lời hứa như một vật cần "giữ" cho khỏi mất. Trái nghĩa: break a promise.|Collocation theo cặp keep/break: keep/break a promise, a secret, one's word.|Dùng ở mọi ngữ cảnh, kể cả trang trọng. Ví dụ: keep one's word cũng có nghĩa tương tự.
break the law|break = phá vỡ; the law = luật|Luật như một hàng rào, làm trái là "phá vỡ" nó.|Cặp keep/break: break the law/a rule/a record/a promise. Trái nghĩa: obey/follow the law.|Dùng trong tin tức, pháp lý và hằng ngày. Nhiều cụm cùng kiểu: break the rules.
make progress|make = tạo ra; progress = sự tiến bộ|Tiến bộ là thứ bạn "tạo ra" dần dần; không nói "do progress".|Collocation: make progress/an effort/a mistake. "Progress" thường không đếm được nên không có "a" trước nó.|Dùng khi nói về học tập, công việc, sức khỏe: make good/great/slow progress.
save money|save = để dành, cứu giữ; money = tiền|"Save" nghĩa là giữ lại, không tiêu hết; tiền được "cứu" khỏi bị chi tiêu.|"Save" có nghĩa gốc là cứu giữ; cũng dùng cho save time, save energy.|Dùng hằng ngày: save money, save up for a car. Trái nghĩa: spend/waste money.
take a look at|take = lấy; a look = một cái nhìn; at = vào|"Lấy" một cái nhìn vào vật gì nên nghĩa là xem qua; nhẹ nhàng hơn chỉ dùng "look".|Kiểu take + a + danh từ hành động (take a look, a walk, a shower) tạo cách nói nhẹ, tự nhiên.|Thân mật đến trung tính; hay dùng khi nhờ ai xem giúp.
fast food|fast = nhanh; food = đồ ăn|Món được chế biến và phục vụ nhanh (bánh burger, gà rán, khoai chiên).|Danh từ ghép cố định, phổ biến cùng sự phát triển của các chuỗi nhà hàng ăn nhanh.|Dùng hằng ngày: fast food restaurant/chain. Thường mang sắc thái không tốt cho sức khỏe.
have a good/great time|have = có; a good time = khoảng thời gian vui|"Have" dùng với trải nghiệm: have fun, have a nice day, have a good time. Không nói "make a good time".|Collocation cố định theo thói quen của người bản xứ.|Rất thân mật: Did you have a good time? Cũng dùng làm lời chúc: Have a great time!
reach a conclusion|reach = với tới, đạt tới; conclusion = kết luận|Kết luận như một "đích đến" mà lập luận dần dần "với tới".|Reach đi với nhiều kết quả trừu tượng: reach an agreement/a decision/a conclusion. Cũng nói come to a conclusion.|Hơi trang trọng: dùng trong họp, nghiên cứu, báo chí.
meet the deadline|meet = gặp, đáp ứng; the deadline = hạn chót|"Meet" còn nghĩa đáp ứng (meet a need/a standard), nên kịp hạn chót là đáp ứng được thời hạn.|Theo nhiều nguồn, "deadline" ban đầu chỉ đường ranh giới trong nhà tù thời Nội chiến Mỹ mà tù nhân vượt qua sẽ bị bắn; nghĩa "hạn chót" đến sau. Cụm meet the deadline là collocation cố định.|Dùng trong công việc, học tập: meet/miss/extend the deadline.
break the ice|break = phá vỡ; ice = băng|Không khí ngượng ngùng lúc mới gặp như lớp băng; phá vỡ nó để mọi người thoải mái trò chuyện.|Thường được giải thích bằng hình ảnh tàu phá băng mở đường cho tàu khác. Nghĩa bóng đã có từ vài trăm năm trước.|Dùng khi gặp người mới, mở đầu buổi họp hay bữa tiệc. Danh từ liên quan: an icebreaker (trò chơi, câu hỏi làm quen).
a piece of cake|a piece = một miếng; cake = bánh|Ăn một miếng bánh là việc dễ chịu, không tốn sức nên chỉ việc rất dễ.|Được ghi nhận từ đầu thế kỷ 20, nhiều khả năng từ tiếng Anh Mỹ.|Thân mật, dùng khi nói một việc, một bài kiểm tra dễ dàng. Không hợp với văn bản rất trang trọng.
once in a blue moon|once = một lần; blue moon = trăng xanh|Trăng xanh hiếm gặp nên cụm này chỉ điều rất hiếm khi xảy ra.|Người ta dùng "blue moon" để chỉ điều hiếm từ lâu. Hiện nay thường hiểu là lần trăng tròn thứ hai trong một tháng dương lịch.|Thân mật, nói về tần suất rất thấp.
under the weather|under = dưới; the weather = thời tiết|Như bị thời tiết "đè" lên nên người thấy mệt, khó chịu, hơi ốm.|Một giả thuyết phổ biến: thủy thủ bị ốm phải xuống dưới boong để tránh thời tiết xấu. Chưa được xác nhận chắc chắn.|Thân mật, dùng cho ốm nhẹ, mệt mỏi: feel/be under the weather. Không dùng cho bệnh nặng.
cost an arm and a leg|cost = tốn, có giá; an arm = một cánh tay; a leg = một cái chân|Phải trả bằng cả tay và chân, cái giá cực lớn nên nghĩa là rất đắt.|Nguồn gốc cụ thể chưa rõ ràng. Hình ảnh dễ hiểu là phải trả giá bằng chính cơ thể mình.|Thân mật, khi than đồ vật hoặc dịch vụ quá đắt.
hit the books|hit = đánh, lao vào; the books = sách vở|"Hit" ở đây gần nghĩa bắt tay ngay vào làm mạnh mẽ (giống hit the road), nên nghĩa là học bài chăm chỉ.|Theo một số từ điển, thành ngữ này xuất hiện trong tiếng Anh Mỹ khoảng đầu thế kỷ 20.|Thân mật, nhất là học sinh, sinh viên trước kỳ thi.
spill the beans|spill = làm đổ; the beans = hạt đậu|Làm đổ đậu khiến thứ giấu bên trong lộ ra nên nghĩa là tiết lộ bí mật.|Một giả thuyết cho rằng từ Hy Lạp cổ: dùng đậu để bỏ phiếu kín, làm đổ hũ thì lộ kết quả. Chưa được xác nhận chắc chắn.|Thân mật, khi lỡ nói ra bí mật hoặc điều bất ngờ: Don't spill the beans!
the ball is in one's court|the ball = quả bóng; court = sân (thi đấu)|Như quần vợt: bóng ở phần sân của ai thì đến lượt người đó đánh, tức đến lượt họ hành động hoặc quyết định.|Hình ảnh lấy từ các môn có sân như quần vợt. Nghĩa bóng phổ biến trong thế kỷ 20. Chú ý "court" ở đây không phải tòa án.|Dùng trong công việc, đàm phán, sau khi mình đã làm phần việc của mình.
kill two birds with one stone|kill = giết, hạ; two birds = hai con chim; one stone = một hòn đá|Một cú ném đá hạ được hai con chim nên nghĩa là một hành động đạt hai mục đích.|Hình ảnh săn chim bằng đá; cách nói được ghi nhận từ vài thế kỷ trước.|Thân mật: dùng khi một việc giải quyết được hai vấn đề cùng lúc.
bite the bullet|bite = cắn; the bullet = viên đạn|Cắn viên đạn để chịu đau nên nghĩa là cắn răng chịu đựng, chấp nhận làm việc khó chịu nhưng cần thiết.|Thường được kể rằng lính bị mổ ngày xưa cắn viên đạn để chịu đau khi chưa có thuốc mê. Đây là cách giải thích phổ biến nhưng chưa có bằng chứng chắc chắn.|Thân mật, hay gặp trong tin tức: bite the bullet and do something.
on the same page|on = trên; the same page = cùng một trang|Cùng đọc một trang giấy nên nghĩa là cùng hiểu và cùng đồng ý với nhau.|Hình ảnh cùng nhìn một trang tài liệu. Thường dùng ở công sở, nhất là tiếng Anh Mỹ.|Dùng trong họp, dự án khi cần chắc chắn mọi người hiểu giống nhau.
call it a day|call = tuyên bố; it = việc đó; a day = một ngày|"Tuyên bố" ngày làm việc đã đủ nên nghĩa là nghỉ, dừng làm việc hôm nay.|Nguồn gốc chưa rõ, được ghi nhận từ khoảng đầu thế kỷ 20.|Thân mật, dùng khi nói với đồng nghiệp hoặc bạn bè lúc kết thúc công việc trong ngày.
beat around the bush|beat = đập, khua; around = xung quanh; the bush = bụi cây|Người đi săn khua bụi cây vòng quanh thay vì đi thẳng vào nên nghĩa là nói vòng vo, không vào thẳng vấn đề.|Thường giải thích từ việc săn chim: người khua bụi rậm cho chim bay ra. Cách nói đã có từ nhiều thế kỷ.|Thân mật, dùng để yêu cầu ai nói thẳng vào vấn đề.
hit the nail on the head|hit = đánh, đập trúng; the nail = cái đinh; the head = mũ đinh (đầu đinh)|Đóng búa trúng ngay mũ đinh thì đinh mới vào chắc, nên nghĩa là nói hoặc làm trúng ngay điểm mấu chốt.|Bắt nguồn từ nghề mộc. Cách nói đã xuất hiện trong tiếng Anh từ khoảng thế kỷ 16.|Thân mật đến trung tính, thường dùng để khen ai nói đúng vấn đề.
get out of hand|get = trở nên; out of = ra khỏi; hand = bàn tay|Không còn "nằm trong tay" mình nên nghĩa là vượt khỏi tầm kiểm soát.|Hình ảnh cầm nắm, kiểm soát bằng tay (có thể liên quan đến việc cầm cương ngựa). Đây là cách giải thích, chưa chắc chắn.|Dùng cho tình huống, đám đông, tình hình mất kiểm soát.
in the same boat|in = trong; the same boat = cùng một con thuyền|Cùng ngồi trên một chiếc thuyền thì chung số phận nên nghĩa là cùng cảnh ngộ.|Ẩn dụ đi thuyền chung. Cách nói đã được dùng từ nhiều thế kỷ trước.|Thân mật, thường dùng để an ủi khi mọi người cùng gặp khó khăn giống nhau.
"""


def load_explain():
    d = {}
    for line in EXPLAIN_TEXT.strip().splitlines():
        p = [x.strip() for x in line.split("|")]
        if len(p) == 5:
            d[p[0]] = dict(zip(("parts", "why", "origin", "use"), p[1:]))
    return d


def load_bank():
    text = BANK_TEXT
    try:
        text += "\n" + Path(__file__).with_name("bank.txt").read_text(encoding="utf-8")
    except Exception:
        pass
    bank, ex = [], load_explain()
    for line in text.splitlines():
        p = [x.strip() for x in line.split("|")]
        if len(p) in (5, 9) and p[0] in ("pv", "col", "idiom") and all(p):
            it = {"id": len(bank), "type": p[0], "expr": p[1], "meaning": p[2], "vi": p[3], "en": p[4],
                  "parts": "", "why": "", "origin": "", "use": ""}
            it.update(ex.get(p[1], {}))
            if len(p) == 9:
                it.update(dict(zip(("parts", "why", "origin", "use"), p[5:])))
            bank.append(it)
    return bank


BANK = load_bank()
VI_CHARS = re.compile(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", re.I)
SKIP_CATEGORIES = {"STYLE", "REDUNDANCY", "PLAIN_ENGLISH", "WIKIPEDIA", "TYPOGRAPHY"}
UA = {"User-Agent": "Mozilla/5.0"}
_cache, _blocked_until = {}, 0


# ---------------- Dịch (chỉ dùng để dịch lời giải thích lỗi sang tiếng Việt) ----------------
def _fj(url, data=None):
    req = urllib.request.Request(url, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode("utf-8"))


def _short(e):
    m = re.search(r"HTTP Error (\d+)", str(e))
    return "lỗi " + m.group(1) if m else "không kết nối được"


def tr(text):
    global _blocked_until
    if text in _cache:
        return _cache[text]
    if time.time() < _blocked_until:
        return ""
    q, email = quote(text, safe=""), os.environ.get("MYMEMORY_EMAIL")
    tries = [
        lambda: "".join(p[0] for p in _fj(f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=vi&dt=t&q={q}")[0] if p[0]),
        lambda: _fj(f"https://lingva.ml/api/v1/en/vi/{q}")["translation"],
        lambda: _fj(f"https://api.mymemory.translated.net/get?q={q}&langpair=en|vi" + (f"&de={quote(email)}" if email else ""))["responseData"]["translatedText"],
    ]
    for t in tries:
        try:
            out = (t() or "").strip()
            if out and not out.upper().startswith("MYMEMORY WARNING"):
                _cache[text] = out
                return out
        except Exception:
            pass
    _blocked_until = time.time() + 60
    return ""


# ---------------- Kiểm tra câu có dùng đúng cụm bắt buộc ----------------
IRREG = {w.split()[0]: w for w in (
    "be am is are was were been being", "get gets got gotten getting", "give gives gave given giving",
    "take takes took taken taking", "make makes made making", "do does did done doing", "go goes went gone going",
    "come comes came coming", "break breaks broke broken breaking", "bring brings brought bringing",
    "catch catches caught catching", "keep keeps kept keeping", "hit hits hitting", "cost costs costing",
    "kill kills killed killing", "spill spills spilled spilt spilling", "put puts putting", "run runs ran running",
    "set sets setting", "find finds found finding", "have has had having", "meet meets met meeting",
    "bite bites bit bitten biting", "beat beats beaten beating", "carry carries carried carrying",
    "tell tells told telling", "say says said saying", "see sees saw seen seeing", "hold holds held holding")}
POSS = {"my", "your", "his", "her", "its", "our", "their", "one's", "whose"}
OPTIONAL = {"a", "an", "the", "is", "are", "am", "sb", "sth", "someone", "something", "somebody"}   # có thể đổi/bỏ


def forms(w):
    f = {w} | set(IRREG.get(w, "").split())
    if w.endswith("e"):
        f |= {w + "s", w + "d", w[:-1] + "ing"}
    elif w.endswith("y") and len(w) > 2 and w[-2] not in "aeiou":
        f |= {w[:-1] + "ies", w[:-1] + "ied", w + "ing"}
    else:
        f |= {w + "s", w + "es", w + "ed", w + "ing", w + w[-1] + "ed", w + w[-1] + "ing"}
    return f


def tok_match(et, ut):
    if et == "one's":
        return ut in POSS or ut.endswith("'s")
    ut2 = ut[:-2] if ut.endswith("'s") else ut
    return any(ut in forms(a) or ut2 in forms(a) for a in et.split("/"))


def uses_expr(expr, ans, gap=4):
    """Cụm phải xuất hiện đúng thứ tự, cho phép chia động từ, đổi a/the/his..., và chen tối đa 4 từ (turn the light off)."""
    toks = [t for t in re.findall(r"[a-z'/]+", expr.lower()) if t not in OPTIONAL]
    words = re.findall(r"[a-z']+", ans.lower().replace("’", "'"))
    for i, w in enumerate(words):
        if not tok_match(toks[0], w):
            continue
        pos, ok = i, True
        for et in toks[1:]:
            nxt = next((j for j in range(pos + 1, min(len(words), pos + gap + 1)) if tok_match(et, words[j])), None)
            if nxt is None:
                ok = False
                break
            pos = nxt
        if ok:
            return True
    return False


# ---------------- Chấm điểm ----------------
STOP = set("the a an is are was were be been am i you he she it we they to of in on at for and or but with my your his her "
           "our their this that these those do does did have has had will would can could should not no so very".split())


def _content(t):
    return [w for w in re.findall(r"[a-z']+", t.lower()) if len(w) > 2 and w not in STOP]


def _same(a, b):
    return a == b or (len(a) >= 4 and len(b) >= 4 and a[:4] == b[:4])


def _norm(t):
    return re.sub(r"[^a-z0-9 ]+", "", t.lower().replace("’", "'").replace("'", "")).split()


def lt_check(text):
    body = urlencode({"text": text, "language": "en-US"}).encode()
    return _fj("https://api.languagetool.org/v2/check", data=body)["matches"]


def grade(item, ans):
    ans, ref = ans.strip(), item["en"]
    if not ans:
        return {"error": "Bạn chưa viết câu trả lời."}
    if VI_CHARS.search(ans):
        return {"error": "Hãy viết câu trả lời bằng tiếng Anh nhé."}
    if _norm(ans) == _norm(ref):        # trùng câu mẫu -> đúng tuyệt đối, khỏi cần gọi dịch vụ ngoài
        return {"score": 10.0, "passed": True, "segments": [{"t": ans, "ok": True}], "errors": [], "corrected": ans,
                "natural": ref, "used": True, "expr": item["expr"], "breakdown": []}
    try:
        raw = lt_check(ans)
    except Exception as e:
        return {"error": f"Không chấm được ngữ pháp lúc này ({_short(e)}). Hãy thử lại sau ít phút."}
    ms = []
    for m in raw:
        tok = ans[m["offset"]:m["offset"] + m["length"]]
        if m["rule"]["category"]["id"] in SKIP_CATEGORIES:
            continue
        if m["rule"]["id"].startswith("MORFOLOGIK") and tok[:1].isupper() and m["offset"] > 0:
            continue                    # tên riêng không tính là lỗi chính tả
        ms.append(m)
    ms.sort(key=lambda m: m["offset"])
    segs, errs, used, cur, gpen = [], [], [], 0, 0.0
    for m in ms:
        o, l = m["offset"], max(1, m["length"])
        if o < cur:
            continue
        if o > cur:
            segs.append({"t": ans[cur:o], "ok": True})
        segs.append({"t": ans[o:o + l], "ok": False})
        fx = [r["value"] for r in m["replacements"][:3]]
        used.append((o, l, fx))
        errs.append({"text": ans[o:o + l], "msg": m["message"], "fix": fx})
        cat = m["rule"]["category"]["id"]
        gpen += 1.0 if cat == "TYPOS" else 0.5 if cat in ("CASING", "PUNCTUATION") else 1.5
        cur = o + l
    if cur < len(ans):
        segs.append({"t": ans[cur:], "ok": True})
    with ThreadPoolExecutor(6) as ex:
        for e, v in zip(errs, ex.map(lambda e: tr(e["msg"]), errs)):
            e["msg"] = v or e["msg"]
    fixed = ans
    for o, l, fx in reversed(used):
        if fx:
            fixed = fixed[:o] + fx[0] + fixed[o + l:]
    has_expr = uses_expr(item["expr"], ans)
    n, refn = len(re.findall(r"[A-Za-z']+", ans)), len(re.findall(r"[A-Za-z']+", ref))
    rc, uc = _content(ref), _content(ans)
    cov = sum(any(_same(r, u) for u in uc) for r in rc) / len(rc) if rc else 1.0
    pen = []
    if gpen:
        pen.append(("Ngữ pháp / chính tả", round(min(7, gpen), 1)))
    if not has_expr:
        pen.append((f"Chưa dùng đúng cụm “{item['expr']}”", 4.0))
    if cov < 0.5:
        pen.append(("Chưa sát nghĩa câu tiếng Việt", round((0.5 - cov) / 0.5 * 3, 1)))
    if refn >= 4 and n < 0.5 * refn:
        pen.append(("Câu quá ngắn, chưa đủ ý", round(min(4, (0.5 * refn - n) * 1.2), 1)))
    pen = [(a, b) for a, b in pen if b > 0]
    passed = not pen
    score = 10.0 if passed else min(9.5, max(0.0, round((10 - sum(b for _, b in pen)) * 2) / 2))
    return {"score": score, "passed": passed, "segments": segs, "errors": errs, "corrected": fixed, "natural": ref,
            "used": has_expr, "expr": item["expr"], "breakdown": [{"label": a, "value": b} for a, b in pen]}


class Handler(BaseHTTPRequestHandler):
    def _send(self, body, ctype):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        p = {k: v[0] for k, v in parse_qs(u.query).items()}
        j = lambda o: self._send(json.dumps(o, ensure_ascii=False), "application/json")
        if u.path == "/":
            self._send(PAGE, "text/html")
        elif u.path == "/api/bank":       # không gửi câu mẫu tiếng Anh cho trình duyệt (chỉ hiện sau khi chấm)
            j([{k: b[k] for k in ("id", "type", "expr", "meaning", "vi", "parts", "why", "origin", "use")} for b in BANK])
        elif u.path == "/api/grade" and p.get("id", "").isdigit() and int(p["id"]) < len(BANK):
            j(grade(BANK[int(p["id"])], p.get("answer", "")))
        else:
            self.send_error(404)

    def log_message(self, *a):
        pass


PAGE = r"""<!DOCTYPE html>
<html lang="vi"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Luyện Phrasal Verb - Collocation - Idiom</title>
<style>
:root{--bg:#faf9f7;--card:#fff;--ink:#1c1a17;--sub:#6b6560;--accent:#b91c1c;--accent-ink:#fff;--line:#e8e4de;--gbg:#dcfce7;--gink:#14532d;--rbg:#fee2e2;--rink:#7f1d1d}
@media (prefers-color-scheme:dark){:root{--bg:#17140f;--card:#211d17;--ink:#f3efe8;--sub:#a39c92;--accent:#f0655a;--accent-ink:#1a1310;--line:#332c22;--gbg:#14532d;--gink:#dcfce7;--rbg:#7f1d1d;--rink:#fee2e2}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;display:flex;justify-content:center;padding:32px 16px}
.wrap{width:100%;max-width:520px}
h1{font-size:1.3rem;margin:0 0 6px}
p.desc{color:var(--sub);margin:0 0 20px;font-size:.95rem;line-height:1.5}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:24px;margin-bottom:16px}
label{display:block;font-size:.85rem;color:var(--sub);margin-bottom:6px;font-weight:600}
textarea,select{width:100%;padding:12px 14px;font-size:1.05rem;border-radius:10px;border:1px solid var(--line);background:var(--bg);color:var(--ink);font-family:inherit}
textarea{resize:vertical}
textarea:focus{outline:2px solid var(--accent);outline-offset:1px}
button.main{flex:1;padding:14px;font-size:1.05rem;font-weight:700;border:none;border-radius:10px;background:var(--accent);color:var(--accent-ink);cursor:pointer}
button.main:disabled{opacity:.5}
button.stop{padding:12px 16px;font-size:1rem;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
.bar{height:8px;background:var(--line);border-radius:6px;overflow:hidden;margin:8px 0 4px}
.bar>div{height:100%;background:#22c55e;transition:width .3s}
.badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:.78rem;font-weight:700;color:#fff}
.req{margin:12px 0;padding:12px 14px;border-radius:10px;background:var(--bg);border:1px dashed var(--accent);line-height:1.5}
.req b{color:var(--accent);font-size:1.15rem}
.exp{margin-top:10px;font-size:.92rem;line-height:1.55}
.exp summary{cursor:pointer;font-weight:700;color:var(--ink)}
.exp div{margin-top:8px}
.exp small{display:block;color:var(--sub);font-weight:700;font-size:.78rem}
.exp span.p{color:var(--ink)}
.vsent{font-size:1.25rem;font-weight:700;margin:6px 0 14px;line-height:1.5}
.score{font-size:2.4rem;font-weight:800;text-align:center}
.ans{font-size:1.15rem;line-height:1.9;margin:10px 0}
.ok{background:var(--gbg);color:var(--gink);border-radius:4px;padding:1px 3px}
.bad{background:var(--rbg);color:var(--rink);border-radius:4px;padding:1px 3px;text-decoration:underline wavy}
.err{padding:10px 12px;border-radius:10px;background:var(--bg);border-left:3px solid #ef4444;margin-bottom:8px;font-size:.92rem;line-height:1.5}
.box{padding:10px 12px;border-radius:10px;background:var(--bg);border-left:3px solid #22c55e;margin-top:8px;font-size:.95rem;line-height:1.5}
.box.warn{border-left-color:#ef4444}
.box small{display:block;color:var(--sub);font-weight:600;margin-bottom:2px}
.link{background:none;border:none;color:var(--accent);cursor:pointer;font-size:1rem;padding:0 4px}
</style></head>
<body><div class="wrap">
<h1>🧩 Luyện Phrasal Verb · Collocation · Idiom</h1>
<p class="desc">Dịch câu tiếng Việt sang tiếng Anh và <b>bắt buộc dùng cụm cho sẵn</b>. Bạn chỉ được sang câu tiếp theo khi đạt <b>10/10</b>.</p>

<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:center;gap:10px">
    <label style="margin:0" id="progText"></label>
    <select id="filter" style="width:auto;padding:6px 10px;font-size:.85rem">
      <option value="all">Tất cả</option><option value="pv">Phrasal verb</option>
      <option value="col">Collocation</option><option value="idiom">Idiom</option></select>
  </div>
  <div class="bar"><div id="progBar" style="width:0%"></div></div>
  <div style="font-size:.75rem;color:var(--sub)" id="lockNote"></div>
</div>

<div class="card" id="exBox">
  <span class="badge" id="badge"></span>
  <div class="req">Bắt buộc dùng: <b id="expr"></b><br><span style="color:var(--sub);font-size:.9rem">Nghĩa: <span id="emean"></span></span>
    <details class="exp" id="exp" open><summary>📖 Diễn giải cụm này</summary>
      <div id="expParts"></div><div id="expWhy"></div><div id="expOrigin"></div><div id="expUse"></div></details></div>
  <label>Dịch sang tiếng Anh:</label>
  <div class="vsent" id="vi"></div>
  <textarea id="answer" rows="3" placeholder="Viết câu tiếng Anh của bạn..."></textarea>
  <div style="display:flex;gap:10px;margin-top:12px"><button class="main" id="gradeBtn" type="button">Chấm bài</button></div>
  <div id="result" style="display:none;margin-top:18px"></div>
  <div style="display:flex;margin-top:14px"><button class="main" id="nextBtn" type="button" style="display:none;background:#16a34a">🎉 Câu tiếp theo ▶️</button></div>
</div>

<div class="card" id="finished" style="display:none;text-align:center">
  <div style="font-size:2.4rem">🏆</div>
  <div style="font-weight:800;margin:6px 0">Bạn đã hoàn thành hết các câu trong mục này!</div>
  <div style="color:var(--sub);font-size:.9rem;margin-bottom:14px">Đổi loại ở ô phía trên, hoặc làm lại từ đầu.</div>
  <button class="stop" id="resetBtn" type="button">🔁 Làm lại từ đầu</button>
</div>
</div>

<script>
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const LS = {get:(k,d)=>{try{const v=localStorage.getItem(k);return v===null?d:JSON.parse(v);}catch(e){return d;}}, set:(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v));}catch(e){}}};
const TYPES = {pv:['Phrasal verb','#2563eb'], col:['Collocation','#16a34a'], idiom:['Idiom','#9333ea']};
let BANK=[], done=new Set(LS.get('pd_done',[])), cur=null, passed=false, filter=LS.get('pd_filter','all');

const say = t => { speechSynthesis.cancel(); const u=new SpeechSynthesisUtterance(t); u.lang='en-US'; speechSynthesis.speak(u); };

function progress(){
  $('progText').textContent = 'Hoàn thành '+done.size+' / '+BANK.length+' câu';
  $('progBar').style.width = (BANK.length ? done.size*100/BANK.length : 0)+'%';
  const locked = !!cur && !passed;
  $('filter').disabled = locked;
  $('lockNote').textContent = locked ? '🔒 Đạt 10/10 để đổi loại hoặc sang câu khác.' : '';
}
function pool(){ return BANK.filter(b => (filter==='all'||b.type===filter) && !done.has(b.id)); }
function nextItem(){
  const p = pool();
  if(!p.length){ cur=null; passed=false; $('exBox').style.display='none'; $('finished').style.display='block'; progress(); return; }
  showItem(p[Math.floor(Math.random()*p.length)]);
}
function showItem(it){
  cur=it; passed=false; LS.set('pd_cur', it.id);
  $('finished').style.display='none'; $('exBox').style.display='block';
  $('badge').textContent=TYPES[it.type][0]; $('badge').style.background=TYPES[it.type][1];
  $('expr').textContent=it.expr; $('emean').textContent=it.meaning;
  const rows = [['expParts','🧩 Nghĩa từng từ',it.parts],['expWhy','🔗 Vì sao gộp lại ra nghĩa này',it.why],['expOrigin','📜 Nguồn gốc / cách hình thành',it.origin],['expUse','🗣️ Ngữ cảnh sử dụng',it.use]];
  rows.forEach(r => { $(r[0]).style.display = r[2] ? 'block' : 'none'; $(r[0]).innerHTML = r[2] ? '<small>'+r[1]+'</small><span class="p">'+esc(r[2])+'</span>' : ''; });
  $('exp').style.display = rows.some(r => r[2]) ? 'block' : 'none'; $('vi').textContent='🇻🇳 '+it.vi;
  $('answer').value=''; $('result').style.display='none'; $('nextBtn').style.display='none'; $('gradeBtn').disabled=false;
  progress();
}
$('filter').value = filter;
$('filter').onchange = () => { filter=$('filter').value; LS.set('pd_filter', filter); nextItem(); };
$('nextBtn').onclick = nextItem;
$('resetBtn').onclick = () => { done=new Set(); LS.set('pd_done', []); nextItem(); };

$('gradeBtn').onclick = async () => {
  if(!cur) return;
  const ans = $('answer').value.trim(); if(!ans) return;
  const btn=$('gradeBtn'); btn.disabled=true; btn.textContent='Đang chấm...';
  const box=$('result'); box.style.display='block'; box.innerHTML='<div style="color:var(--sub)">Đang chấm bài...</div>';
  try{
    const r = await (await fetch('/api/grade?id='+cur.id+'&answer='+encodeURIComponent(ans))).json();
    if(r.error){ box.innerHTML='<div class="err">⚠️ '+esc(r.error)+'</div>'; }
    else{
      const col = r.passed?'#16a34a':r.score>=7?'#d97706':'#dc2626';
      box.innerHTML =
        '<div class="score" style="color:'+col+'">'+r.score+' / 10</div>'+
        '<div style="text-align:center;color:var(--sub);margin-bottom:6px">'+(r.passed?'Hoàn hảo! Bạn được sang câu tiếp 🎉':'Chưa đủ 10 điểm — sửa lại rồi chấm lại nhé')+'</div>'+
        (r.breakdown.length ? '<div style="text-align:center;font-size:.8rem;color:var(--sub);margin-bottom:10px">'+r.breakdown.map(b => esc(b.label)+' −'+b.value).join(' · ')+'</div>' : '')+
        '<div class="ans">'+r.segments.map(s => '<span class="'+(s.ok?'ok':'bad')+'">'+esc(s.t)+'</span>').join('')+'</div>'+
        '<div class="box'+(r.used?'':' warn')+'"><small>🎯 Cụm bắt buộc: '+esc(r.expr)+'</small>'+(r.used?'✅ Bạn đã dùng đúng cụm này.':'❌ Chưa thấy cụm này (hoặc dùng sai dạng/thứ tự) trong câu của bạn.')+'</div>'+
        (r.errors.length ? '<label style="margin-top:14px">Lỗi cần sửa ('+r.errors.length+')</label>'+r.errors.map(e =>
          '<div class="err"><b>“'+esc(e.text)+'”</b> — '+esc(e.msg)+(e.fix.length?'<br>Gợi ý sửa: <b>'+e.fix.map(esc).join(' / ')+'</b>':'')+'</div>').join('') : '')+
        (r.errors.length ? '<div class="box"><small>✅ Câu sau khi sửa lỗi</small>'+esc(r.corrected)+'</div>' : '')+
        '<div class="box"><small>💡 Gợi ý cách viết tự nhiên hơn</small>'+esc(r.natural)+' <button class="link" id="sayNat" type="button">🔊</button></div>'+
        '<div style="font-size:.78rem;color:var(--sub);margin-top:10px;line-height:1.5">Xanh = đúng, đỏ = lỗi. Để đạt 10/10: không có lỗi ngữ pháp, dùng đúng cụm bắt buộc và diễn đạt đủ ý câu tiếng Việt (cho phép diễn đạt khác câu mẫu).</div>';
      $('sayNat').onclick = () => say(r.natural);
      if(r.passed){
        passed=true; done.add(cur.id); LS.set('pd_done', [...done]);
        $('nextBtn').style.display='block'; progress();
      }
    }
  }catch(e){ box.innerHTML='<div class="err">⚠️ Không chấm được lúc này, thử lại nhé.</div>'; }
  btn.disabled=false; btn.textContent='Chấm bài';
};
$('answer').addEventListener('keydown', e => { if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); $('gradeBtn').click(); } });

(async function init(){
  try{ BANK = await (await fetch('/api/bank')).json(); }catch(e){ $('vi').textContent='Không tải được dữ liệu.'; return; }
  const saved = BANK.find(b => b.id===LS.get('pd_cur', null));
  if(saved && !done.has(saved.id)) showItem(saved); else nextItem();    // tải lại trang vẫn giữ nguyên câu chưa đạt
})();
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8002)))
    ap.add_argument("--lan", action="store_true", help="cho điện thoại cùng Wi-Fi truy cập")
    a = ap.parse_args()
    host = "0.0.0.0" if (a.lan or "PORT" in os.environ) else "127.0.0.1"
    print(f"Có {len(BANK)} câu. Mở trình duyệt: http://localhost:{a.port}")
    if a.lan:
        print(f"Điện thoại (cùng Wi-Fi): http://{socket.gethostbyname(socket.gethostname())}:{a.port}")
    print("Nhấn Ctrl+C để tắt.")
    ThreadingHTTPServer((host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
