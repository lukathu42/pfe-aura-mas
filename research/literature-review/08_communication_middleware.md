# Communication Middleware for Multi-Agent Surveillance Systems: A Comparative Analysis

## 1. Key Concepts and Definitions

In the context of an "Agentic multi-agent intelligent surveillance system," communication middleware serves as the central nervous system, enabling distributed sensors, edge devices, and central servers to exchange data efficiently. The architecture of such systems is inherently **Event-Driven Architecture (EDA)**, where state changes (e.g., a person detected, an anomaly recognized) are broadcasted as events rather than polled synchronously.

### 1.1. Core Middleware Paradigms
- **Message-Oriented Middleware (MOM):** Software infrastructure that supports sending and receiving distributed messages.
- **Publish/Subscribe (Pub/Sub):** A messaging pattern where senders (publishers) categorize messages into topics without knowledge of specific receivers (subscribers).
- **Broker vs. Brokerless:** Broker-based systems (e.g., MQTT, Kafka) route messages through a central server, while brokerless systems (e.g., ZeroMQ, DDS) establish direct peer-to-peer connections.

### 1.2. Quality of Service (QoS) and Delivery Semantics
- **At-Most-Once (QoS 0):** Fire-and-forget. Messages may be lost but are never duplicated. Suitable for high-frequency telemetry where occasional loss is acceptable.
- **At-Least-Once (QoS 1):** Guaranteed delivery, but duplicates may occur. Requires consumer idempotency.
- **Exactly-Once Semantics (EOS / QoS 2):** The highest guarantee, ensuring a message is processed exactly once. Critical for financial transactions or critical security alerts, though it introduces significant latency overhead.

---

## 2. State of the Art and Comparative Analysis

The landscape of communication middleware offers diverse solutions, each optimized for specific network topologies and workloads. Recent benchmarking studies, such as those by Arafat et al. (2025) and Zhang et al. (2024), provide quantitative insights into their performance.

### 2.1. MQTT (Message Queuing Telemetry Transport)
MQTT is a lightweight, broker-based pub/sub protocol designed for constrained devices and low-bandwidth, high-latency networks.
- **Pros:** Extremely low overhead, built-in QoS levels (0, 1, 2), retained messages, and Last Will and Testament (LWT) features.
- **Cons:** Centralized broker can become a bottleneck; lacks native stream processing capabilities.
- **Performance:** Excels in Wi-Fi and 4G environments. Zhang et al. (2024) demonstrated that MQTT and Zenoh outperform DDS in wireless edge-to-cloud scenarios due to lower discovery overhead.

### 2.2. Apache Kafka
Kafka is a distributed event streaming platform built on an append-only log architecture.
- **Pros:** Massive throughput, persistent storage, native Exactly-Once Semantics (EOS), and replayability.
- **Cons:** High operational complexity, JVM overhead, and overkill for resource-constrained edge devices.
- **Performance:** Arafat et al. (2025) benchmarked Kafka at a peak throughput of ~1.2 million messages/sec with an 18ms p95 latency under optimal conditions, making it the gold standard for heavy backend aggregation.

### 2.3. ROS 2 and DDS (Data Distribution Service)
ROS 2 utilizes DDS as its default middleware (RMW), providing a decentralized, data-centric communication model.
- **Pros:** Real-time capabilities, rich QoS policies (e.g., deadline, lifespan, reliability), and seamless integration with robotics ecosystems.
- **Cons:** DDS discovery protocols (e.g., multicast) struggle in open or wireless environments, often causing network flooding.
- **Performance:** CycloneDDS performs exceptionally well over Ethernet but degrades over Wi-Fi compared to MQTT or Zenoh (Zhang et al., 2024).

### 2.4. ZeroMQ
ZeroMQ is a high-performance asynchronous messaging library aimed at use in distributed or concurrent applications.
- **Pros:** Brokerless, ultra-low latency, supports complex topologies (REQ-REP, PUB-SUB, PUSH-PULL).
- **Cons:** No persistent storage, no built-in QoS delivery guarantees (relies on TCP reliability), requires manual handling of node discovery.
- **Performance:** Offers sub-millisecond latency, ideal for tightly coupled edge-to-edge inter-process communication (IPC).

### 2.5. Redis Streams
Introduced in Redis 5.0, Redis Streams models a log data structure in-memory.
- **Pros:** In-memory speed, consumer groups (similar to Kafka), lightweight deployment.
- **Cons:** Limited by available RAM (though disk persistence exists, it's not its primary strength compared to Kafka).
- **Performance:** Bridges the gap between ZeroMQ's speed and Kafka's consumer group semantics, offering excellent throughput for mid-scale systems.

---

## 3. Message Schemas for Detections, Tracks, and Alerts

For a hierarchical multi-agent surveillance system, standardizing message schemas is critical for interoperability between heterogeneous sensors (cameras, LiDAR, audio). JSON is ubiquitous but verbose; Protobuf or FlatBuffers are recommended for high-frequency data.

### 3.1. Detections (High Frequency, QoS 0)
Raw detections from edge nodes (e.g., YOLOv11 inference).
```json
{
  "timestamp": 1716384920.123,
  "sensor_id": "cam_warehouse_01",
  "frame_id": 4592,
  "objects": [
    {"class": "person", "confidence": 0.92, "bbox": [120, 45, 200, 310]},
    {"class": "forklift", "confidence": 0.88, "bbox": [400, 150, 600, 400]}
  ]
}
```

### 3.2. Tracks (Medium Frequency, QoS 0 or 1)
Processed trajectories from multi-object trackers (e.g., ByteTrack) coordinating across cameras.
```json
{
  "timestamp": 1716384920.500,
  "track_id": "global_trk_883",
  "state": "active",
  "world_coordinates": [34.5, 12.2, 0.0],
  "velocity": [1.2, 0.5, 0.0]
}
```

### 3.3. Alerts (Low Frequency, QoS 2 / Exactly-Once)
Explainable alerts generated by the central reasoning agent.
```json
{
  "alert_id": "alt_9921",
  "timestamp": 1716384921.000,
  "priority": "CRITICAL",
  "event_type": "UNAUTHORIZED_ACCESS",
  "description": "Person detected in restricted Zone B during off-hours.",
  "evidence": ["cam_warehouse_01_frame_4592.jpg"],
  "agents_involved": ["edge_node_1", "central_reasoner"]
}
```

---

## 4. Practical Implementation Guidance

### 4.1. Python Libraries and Tooling
- **MQTT:** `paho-mqtt` (v2.0+). Use Eclipse Mosquitto as the broker.
- **Kafka:** `confluent-kafka-python` (C-extension based, much faster than `kafka-python`).
- **ROS 2:** `rclpy` (Humble or Jazzy distributions).
- **ZeroMQ:** `pyzmq`.
- **Redis:** `redis-py` utilizing the `xadd` and `xreadgroup` functions for Streams.

### 4.2. Hardware Requirements
- **Edge Nodes (Sensors/Cameras):** NVIDIA Jetson Orin Nano / Raspberry Pi 5. Capable of running lightweight MQTT clients or ZeroMQ sockets alongside YOLO inference.
- **Fog/Local Server (Warehouse Campus):** Standard x86 Server (e.g., Intel i7, 32GB RAM, RTX 4060). Runs the MQTT Broker, Redis instance, and multi-camera tracking logic.
- **Cloud/Central Hub:** AWS/GCP instances running Kafka clusters for long-term archiving and global analytics.

---

## 5. Integration into the Thesis Architecture

The proposed thesis architecture is a **"privacy-aware, edge-first, hierarchical multi-agent system for multimodal event detection, inter-sensor coordination, and explainable alerting on a semi-closed site."**

To realize this, a **hybrid middleware approach** is optimal:

1. **Edge-to-Edge (Inter-Sensor Coordination):** Use **ZeroMQ** or **ROS 2 (with Zenoh RMW)**. When two overlapping cameras need to resolve a re-identification (ReID) conflict, they require sub-millisecond, peer-to-peer communication without routing through a central broker.
2. **Edge-to-Fog (Detections to Local Server):** Use **MQTT**. Edge nodes publish their lightweight JSON/Protobuf detection schemas to a local Mosquitto broker. MQTT's QoS 0 is sufficient here, as dropping a single frame's detection is negligible at 30 FPS.
3. **Fog-to-Cloud / Alerting (Explainable Alerts):** Use **Redis Streams** or **Kafka**. Once the local server's reasoning agent generates a critical alert, it must be reliably delivered to the security dashboard. Kafka's Exactly-Once Semantics ensures security personnel do not receive duplicate alerts, and the event is permanently logged for auditing.

---

## 6. Pitfalls and Recommendations for a 1-Month Accelerated Implementation

### 6.1. Common Pitfalls
- **The Kafka Trap:** Attempting to deploy and tune a Zookeeper/KRaft-backed Kafka cluster for a localized warehouse prototype will consume weeks of development time. It is notoriously difficult to configure correctly for small-scale, rapid prototyping.
- **DDS Discovery Storms:** Using default ROS 2 DDS over a campus Wi-Fi network will likely result in packet loss and discovery failures due to multicast limitations on commercial routers.
- **Serialization Bottlenecks:** Sending base64-encoded images over MQTT or Kafka will choke the network and CPU.

### 6.2. Recommendations for 1-Month Implementation
For a rapid, 1-month Master's thesis implementation, **simplicity and reliability are paramount**.

1. **Recommended Stack:** **MQTT + Redis Streams + JSON**.
2. **Architecture:**
   - Run an **Eclipse Mosquitto** broker on the central server.
   - Edge agents (Python scripts on laptops/Jetsons) use `paho-mqtt` to publish bounding boxes and metadata.
   - The central reasoning agent subscribes to MQTT, aggregates data, and pushes high-level alerts to **Redis Streams**.
   - The frontend dashboard consumes from Redis Streams.
3. **Media Handling:** Do not send video frames through the middleware. Edge nodes should save images to a local shared directory or an in-memory store (like Redis) and send only the **file path/URL** in the MQTT message payload.
4. **Avoid ROS 2 unless doing physical robotics:** If the "agents" are static cameras and software processes rather than mobile robots, the overhead of ROS 2 workspaces, colcon builds, and DDS tuning is unnecessary. Stick to pure Python with MQTT/Redis.

---

## 7. Bibliography

```bibtex
@article{zhang2024comparison,
  title={Comparison of Middlewares in Edge-to-Edge and Edge-to-Cloud Communication for Distributed ROS 2 Systems},
  author={Zhang, Jiaqiang and Yu, Xianjia and Ha, Sier and Queralta, Jorge Pe{\~n}a and Westerlund, Tomi},
  journal={arXiv preprint arXiv:2309.07496v4},
  year={2024},
  url={https://arxiv.org/abs/2309.07496}
}

@article{arafat2025nextgen,
  title={Next-Generation Event-Driven Architectures: Performance, Scalability, and Intelligent Orchestration Across Messaging Frameworks},
  author={Arafat, Jahidul and Tasmin, Fariha and Poudel, Sanjaya and Tareq, Ahsan Habib},
  journal={arXiv preprint arXiv:2510.04404v1},
  year={2025},
  url={https://arxiv.org/abs/2510.04404}
}

@article{almanasrah2026message,
  title={Message-Oriented Middleware Systems: Technology Overview},
  author={Al-Manasrah, Wael and AlSader, Zuhair and Brecht, Tim and Alquraan, Ahmed and Al-Kiswany, Samer},
  journal={arXiv preprint arXiv:2602.17774},
  year={2026},
  url={https://arxiv.org/abs/2602.17774}
}

@article{melancon2026blazeaiot,
  title={BlazeAIoT: A Modular Multi-Layer Platform for Real-Time Distributed Robotics Across Edge, Fog, and Cloud Infrastructures},
  author={Melancon, Cedric and Gascon-Samson, Julien and Saad, Maarouf and Kaur, Kuljeet and Savard, Simon},
  journal={arXiv preprint arXiv:2601.06344},
  year={2026},
  url={https://arxiv.org/abs/2601.06344}
}

@article{angela2026internet,
  title={The Internet of Humanoids: A Survey of Technologies, Applications, and Challenges},
  author={Angela, WY and Nayak, A},
  journal={IEEE Internet of Things Journal},
  year={2026},
  url={https://ieeexplore.ieee.org/abstract/document/11346994/}
}

@mastersthesis{gulotta2023realtime,
  title={Real time, dynamic cloud offloading for self-driving vehicles with secure and reliable automatic switching between local and edge computing},
  author={Gulotta, DP},
  school={Politecnico di Torino},
  year={2023},
  url={https://webthesis.biblio.polito.it/27759/}
}

@inproceedings{yoshino2025high,
  title={High Communication Performance Internet of Robotic Things Systems},
  author={Yoshino, D},
  booktitle={IEEE International Conference on Robotics and Automation},
  year={2025},
  url={https://ieeexplore.ieee.org/iel8/6287639/10820123/11278021.pdf}
}

@article{light2017mosquitto,
  title={Mosquitto: server and client implementation of the MQTT protocol},
  author={Light, Roger A},
  journal={The Journal of Open Source Software},
  volume={2},
  number={13},
  pages={265},
  year={2017}
}
```
