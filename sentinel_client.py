import cv2
import time
from ultralytics import YOLO

MODEL_PATH = "models/yolov8n.onnx" 
CONF_THRESHOLD = 0.5 
LINE_RATIO = 0.6 

# Segment 1: p1 to p2 (Tripwire)
# Segment 2: p3 to p4 (Object's path: Previous->Current)
def ccw(A, B, C):
    return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

def intersect(p1, p2, p3, p4):
    return ccw(p1,p3,p4) != ccw(p2,p3,p4) and ccw(p1,p2,p3) != ccw(p1,p2,p4)

def main():
    print(f"Loading Optimized Model: {MODEL_PATH}...")
    try:
        model = YOLO(MODEL_PATH, task='detect') 
    except Exception as e:
        print(f"Error loading ONNX model: {e}")
        return

    # Change to filename 'traffic.mp4' if needed
    cap = cv2.VideoCapture(0)
    
    # STATE VARIABLES (The "Memory")
    # Stores previous center (cx, cy) for every ID: {id: (cx, cy)}
    track_history = {} 
    
    # Keeps track of IDs already counted 
    counted_ids = set()
    
    in_count = 0
    out_count = 0

    while True:
        start_time = time.time()
        ret, frame = cap.read()
        if not ret:
            # Use next line to loop traffic.mp4
            # cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            break

        height, width, _ = frame.shape
        line_y = int(height * LINE_RATIO) # Calculate actual pixel Y coordinate

        # RUN TRACKING (ByteTrack)
        results = model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)
        
        # PROCESS TRACKS
        if results[0].boxes.id is not None:
            # Get the boxes (xyxy), IDs, and Classes
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            classes = results[0].boxes.cls.int().cpu().tolist()

            # Loop through every detected object
            for box, track_id, cls in zip(boxes, track_ids, classes):
                              
                # Calculate Centroid 
                x1, y1, x2, y2 = box
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                
                if track_id in track_history:
                    prev_cx, prev_cy = track_history[track_id]
                    
                    # Define points for easier reading
                    # The Tripwire
                    p1 = (0, int(height * LINE_RATIO))      # Left point
                    p2 = (width, int(height * LINE_RATIO))  # Right point (Horizontal for now)
                    
                    # Path
                    p3 = (prev_cx, prev_cy) # Where it was
                    p4 = (cx, cy)           # Where it is now

                    # Vector Intersection
                    if intersect(p1, p2, p3, p4):
                        if track_id not in counted_ids:
                            # Was it moving down?
                            if cy > prev_cy: 
                                in_count += 1
                                cv2.line(frame, p1, p2, (0, 255, 0), 4) # Green Flash
                            else:
                                out_count += 1
                                cv2.line(frame, p1, p2, (0, 0, 255), 4) # Red Flash
                            
                            counted_ids.add(track_id)

                # Update Memory
                track_history[track_id] = (cx, cy)

                # Draw Box & ID
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 200, 0), 2)
                cv2.putText(frame, f"ID: {track_id}", (int(x1), int(y1)-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
                # Draw Center Dot
                cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)

        # DRAW UI
        # Tripwire Line
        cv2.line(frame, (0, line_y), (width, line_y), (255, 0, 255), 2)
        
        # Stats Dashboard
        cv2.rectangle(frame, (0, 0), (250, 100), (0, 0, 0), -1) # Background for text
        fps = 1.0 / (time.time() - start_time)
        cv2.putText(frame, f"FPS: {fps:.1f} (ONNX)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"IN: {in_count}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, f"OUT: {out_count}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 255), 2)

        cv2.imshow("Sentinel V3 (Counting Logic)", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()