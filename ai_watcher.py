import cv2
import requests
import os
import time
import threading
import numpy as np
from deepface import DeepFace

# الإعدادات
BASE_URL = "http://127.0.0.1:8000"
API_MATCH_URL = f"{BASE_URL}/detections/match"
API_MISSING_URL = f"{BASE_URL}/missing-persons/all"
RTSP_URL = "rtsp://admin:Miroahlawe@@Yu1@192.168.1.103:554/unicast/c1/s0/live" 

known_faces_data = [] 
is_analyzing = False
matched_person = None 
last_send_time = 0

def load_known_faces():
    global known_faces_data
    print("📡 جاري تحميل قاعدة بيانات المفقودين...")
    try:
        response = requests.get(API_MISSING_URL)
        if response.status_code != 200:
            print(f"⚠️ السيرفر رد بخطأ {response.status_code}")
            return

        missing_persons = response.json()
        for person in missing_persons:
            image_url = person.get('image_url')
            if not image_url: continue

            image_filename = os.path.basename(image_url)
            possible_paths = [
                os.path.join("backend", "uploads", "missing_persons", image_filename),
                os.path.join("uploads", "missing_persons", image_filename)
            ]
            
            local_image_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    local_image_path = path
                    break

            if local_image_path:
                print(f"✅ لقيت صورة: {person['name']}")
                try:
                    # نستخدم VGG-Face مع الـ Alignment لزيادة الدقة
                    embedding_objs = DeepFace.represent(
                        img_path=local_image_path, 
                        model_name="VGG-Face",
                        enforce_detection=False,
                        detector_backend="opencv",
                        align=True # دي بتخلي الـ VGG يسنتر الوش صح
                    )
                    embedding = embedding_objs[0]["embedding"]
                    known_faces_data.append({
                        "embedding": embedding,
                        "name": person['name'],
                        "id": person.get('person_id') or person.get('id')
                    })
                except Exception as e:
                    print(f"❌ خطأ في معالجة {person['name']}")
        print(f"🏁 النتيجة: تم تحميل {len(known_faces_data)} شخص بنجاح.")
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")

def analyze_face(frame_to_analyze):
    global is_analyzing, matched_person
    
    if not known_faces_data:
        is_analyzing = False
        return

    try:
        # استخدام VGG-Face للتحليل
        current_face_objs = DeepFace.represent(
            img_path=frame_to_analyze, 
            model_name="VGG-Face",
            enforce_detection=False, 
            detector_backend="opencv",
            align=True # مهمة جداً عشان الدقة ترفع عن 60%
        )
        current_embedding = current_face_objs[0]["embedding"]
        
        best_match = None
        min_dist = 1.0 
        
        for person_data in known_faces_data:
            a = np.array(current_embedding)
            b = np.array(person_data["embedding"])
            # حساب الـ Cosine Distance
            dist = 1 - (np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
            confidence = (1 - dist) * 100

            # عتبة القبول: 0.55 مناسبة جداً للـ VGG
            if dist < 0.55 and dist < min_dist:
                min_dist = dist
                best_match = person_data.copy()
                best_match["confidence"] = round(confidence, 2)
                print(f"🧐 تطابق: {person_data['name']} | الثقة: {confidence:.2f}%")
        
        matched_person = best_match 
            
    except Exception:
        matched_person = None 
        
    is_analyzing = False

# تشغيل الكاميرا
cap = cv2.VideoCapture(RTSP_URL) 
load_known_faces()
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

while True:
    ret, frame = cap.read()
    if not ret: break

    display_frame = cv2.resize(frame, (1280, 720))
    gray = cv2.cvtColor(display_frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        matched_person = None

    for (x, y, w, h) in faces:
        if matched_person:
            color = (0, 255, 0) # أخضر
            label = f"{matched_person['name']} {matched_person['confidence']}%"
        else:
            color = (0, 0, 255) # أحمر
            label = "Searching..."

        cv2.rectangle(display_frame, (x, y), (x+w, y+h), color, 2)
        cv2.putText(display_frame, label, (x, y-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    if len(faces) > 0 and not is_analyzing:
        is_analyzing = True
        threading.Thread(target=analyze_face, args=(display_frame.copy(),)).start()

    # إرسال البلاغ للسيرفر لو الثقة أعلى من 70%
    if matched_person and matched_person['confidence'] > 70:
        current_time = time.time()
        if current_time - last_send_time > 30: 
            print(f"🚨 ALERT: إرسال {matched_person['name']} للسيرفر...")
            temp_file = "match_found.jpg"
            cv2.imwrite(temp_file, display_frame)
            payload = {
                "person_id": matched_person['id'], 
                "confidence_level": matched_person['confidence'] / 100, 
                "location": "Main Entrance", 
                "camera_id": 1
            }
            try:
                with open(temp_file, "rb") as f:
                    files = {"image": ("match.jpg", f, "image/jpeg")}
                    requests.post(API_MATCH_URL, data=payload, files=files)
            except:
                print("❌ فشل إرسال الإشعار.")
            if os.path.exists(temp_file): os.remove(temp_file)
            last_send_time = current_time

    cv2.imshow("VGG-Face Monitor", display_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()