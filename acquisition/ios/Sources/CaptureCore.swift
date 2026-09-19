import Foundation
import CryptoKit

struct CaptureBlock: Codable {
    let sequence: Int
    let first_frame: Int
    let frame_count: Int
    let sample_time_valid: Bool
    let sample_time: String?
    let host_time_valid: Bool
    let host_time: String?
}
struct CaptureEvent: Codable {
    let type: String
    let at_frame: Int
    let detail: String
}
struct SourceDeclaration: Codable {
    let configuration_id: String
    let probe_id: String
    let route_id: String
}
struct RouteSnapshot: Codable, Equatable {
    let input_port_type: String
    let input_port_name: String
    let input_channel_count: Int
    let input_sample_rate_hz: Int
}
struct SessionSnapshot: Codable {
    let category: String
    let mode: String
    let preferred_sample_rate_hz: Int
    let activated_sample_rate_hz: Int
}
struct RecorderIdentity: Codable { let name: String; let version: String }
struct DeviceSnapshot: Codable { let model: String; let os_version: String }
struct HostTimebase: Codable { let numer: UInt32; let denom: UInt32 }
struct ContinuitySnapshot: Codable {
    let status: String
    let reasons: [String]
    let blocks: [CaptureBlock]
}
struct CaptureManifest: Encodable {
    let schema_version = "1.0"
    let format = "echosight_capture"
    let capture_id: String
    let recording_sha256: String
    let sample_encoding = "ieee_float32_le"
    let sample_rate_hz: Int
    let channel_count = 1
    let frame_count: Int
    let recorder = RecorderIdentity(name: "EchoSight native capture", version: "0.1.0")
    let acquisition_layer = "ios_audioengine_delivered_buffers"
    let device: DeviceSnapshot
    let source_declaration: SourceDeclaration
    let session: SessionSnapshot
    let route_initial: RouteSnapshot
    let route_final: RouteSnapshot
    let host_timebase: HostTimebase
    let continuity: ContinuitySnapshot
    let events: [CaptureEvent]
}
struct CaptureSnapshot {
    let sampleRate: Int
    let samples: [Float]
    let blocks: [CaptureBlock]
    let events: [CaptureEvent]
    let reasons: [String]
    let closed: Bool
}
enum CaptureError: Error, CustomStringConvertible {
    case invalid(String)
    var description: String { switch self { case .invalid(let text): return text } }
}

/// Retains immutable capture evidence across encoding/write failures while the
/// process remains alive. Call attempt only on the single export queue.
final class CapturePendingSave {
    private let encode: () throws -> Data
    private let persist: (Data) throws -> URL
    private var encoded: Data?
    init(encode: @escaping () throws -> Data, persist: @escaping (Data) throws -> URL) {
        self.encode = encode; self.persist = persist
    }
    func attempt() throws -> URL {
        if encoded == nil { encoded = try encode() }
        return try persist(encoded!)
    }
}

/// Bounded collector; the lock protects only short memory/state operations.
/// No file encoding, I/O, callbacks, or UI work occurs while it is held.
final class CaptureCollector {
    private let lock = NSLock()
    let sampleRate: Int
    let maximumFrames: Int
    let maximumBlocks: Int
    private let hostTickSeconds: Double
    private var storage: [Float]
    private var retained = 0
    private var blocks: [CaptureBlock] = []
    private var events: [CaptureEvent] = []
    private var reasons: [String] = []
    private var closed = false

    init(sampleRate: Int, seconds: Int = 20, maximumBlocks: Int = 4096,
         hostTimebase: HostTimebase = HostTimebase(numer: 1, denom: 1)) throws {
        guard (8000...192000).contains(sampleRate), (1...20).contains(seconds),
              (1...4096).contains(maximumBlocks), hostTimebase.numer > 0,
              hostTimebase.denom > 0 else { throw CaptureError.invalid("Invalid capture bounds or timebase") }
        self.sampleRate = sampleRate
        self.maximumFrames = sampleRate * seconds
        self.maximumBlocks = maximumBlocks
        self.hostTickSeconds = Double(hostTimebase.numer) / Double(hostTimebase.denom) / 1e9
        storage = [Float](repeating: 0, count: maximumFrames)
        blocks.reserveCapacity(maximumBlocks)
        events.reserveCapacity(64)
        reasons.reserveCapacity(16)
    }
    var frameCount: Int { lock.lock(); defer { lock.unlock() }; return retained }

    private func rejectLocked(_ type: String, _ detail: String) {
        if !reasons.contains(type) { reasons.append(type) }
        if events.count < 64 {
            events.append(CaptureEvent(type: type, at_frame: retained, detail: String(detail.prefix(200))))
        }
        closed = true
    }

    /// Returns a stop reason, nil while active, or "closed" after admission ends.
    /// Invalid timestamps are preserved on their delivered block and invalidate
    /// the shot. Invalid/nonfinite formats are rejected before copying samples.
    func append(_ input: UnsafeBufferPointer<Float>, sampleRate: Double,
                sampleTime: Int64?, hostTime: UInt64?) -> String? {
        lock.lock(); defer { lock.unlock() }
        if closed { return "closed" }
        guard sampleRate == Double(self.sampleRate), !input.isEmpty else {
            rejectLocked("format_changed", "Unexpected delivered sample rate or empty buffer")
            return "format_changed"
        }
        guard blocks.count < maximumBlocks else {
            rejectLocked("buffer_overrun", "Bounded block metadata capacity reached")
            return "buffer_overrun"
        }
        let count = min(input.count, maximumFrames - retained)
        guard count > 0 else { return "duration_limit" }
        // Inspect the retained portion without modifying or normalizing values.
        for index in 0..<count where !input[index].isFinite {
            rejectLocked("nonfinite_samples", "Delivered buffer contains a nonfinite sample")
            return "nonfinite_samples"
        }
        let old = blocks.last
        let block = CaptureBlock(sequence: blocks.count, first_frame: retained, frame_count: count,
            sample_time_valid: sampleTime != nil, sample_time: sampleTime.map(String.init),
            host_time_valid: hostTime != nil, host_time: hostTime.map(String.init))
        storage.withUnsafeMutableBufferPointer { destination in
            destination.baseAddress!.advanced(by: retained).update(from: input.baseAddress!, count: count)
        }
        retained += count
        blocks.append(block)
        if sampleTime == nil || hostTime == nil {
            rejectLocked("timestamp_invalid", "Sample or host timestamp is unavailable")
            return "timestamp_invalid"
        }
        if hostTickSeconds > 0.1 / Double(self.sampleRate) {
            rejectLocked("timestamp_invalid", "Host timebase is too coarse to qualify sample continuity")
            return "timestamp_invalid"
        }
        if let previous = old, let previousSample = previous.sample_time.flatMap(Int64.init),
           let previousHost = previous.host_time.flatMap(UInt64.init) {
            let expected = previousSample.addingReportingOverflow(Int64(previous.frame_count))
            if expected.overflow || sampleTime! != expected.partialValue || hostTime! <= previousHost {
                rejectLocked("timestamp_invalid", "Nonadjacent sample timestamp or nonincreasing host time")
                return "timestamp_invalid"
            }
        }
        // A monotonic host clock alone does not establish a coherent sample
        // clock. Check both adjacent blocks and accumulated drift from start.
        // This conservative admission bound is not physical clock calibration.
        for origin in [old, blocks.count > 1 ? blocks.first : nil].compactMap({ $0 }) {
            guard let startSample = origin.sample_time.flatMap(Int64.init),
                  let startHost = origin.host_time.flatMap(UInt64.init) else { continue }
            let delta = sampleTime!.subtractingReportingOverflow(startSample)
            guard !delta.overflow, delta.partialValue > 0, hostTime! > startHost else {
                rejectLocked("timestamp_invalid", "Invalid sample/host elapsed time")
                return "timestamp_invalid"
            }
            let sampleElapsed = Double(delta.partialValue) / Double(self.sampleRate)
            let hostElapsed = Double(hostTime! - startHost) * hostTickSeconds
            let allowance = 0.01 * sampleElapsed + 2 / Double(self.sampleRate) + 2 * hostTickSeconds
            if abs(hostElapsed - sampleElapsed) > allowance {
                rejectLocked("timestamp_invalid", "Host and sample elapsed time are inconsistent")
                return "timestamp_invalid"
            }
        }
        if retained == maximumFrames {
            events.append(CaptureEvent(type: "duration_limit", at_frame: retained, detail: "Configured recording frame cap reached"))
            closed = true
            return "duration_limit"
        }
        return nil
    }
    func append(_ samples: [Float], sampleRate: Double, sampleTime: Int64?, hostTime: UInt64?) -> String? {
        samples.withUnsafeBufferPointer { append($0, sampleRate: sampleRate, sampleTime: sampleTime, hostTime: hostTime) }
    }
    func finish(_ reason: String, detail: String = "") {
        lock.lock(); defer { lock.unlock() }
        if reason == "user_stop" || reason == "duration_limit" {
            if !closed, events.count < 64 { events.append(CaptureEvent(type: reason, at_frame: retained, detail: detail.isEmpty ? "Recorder stopped: " + reason : String(detail.prefix(200)))) }
            closed = true
        } else {
            rejectLocked(reason, detail)
        }
    }
    func snapshot() throws -> CaptureSnapshot {
        lock.lock(); defer { lock.unlock() }
        guard closed else { throw CaptureError.invalid("Stop capture before export") }
        guard retained > 0 else { throw CaptureError.invalid("No delivered samples to export") }
        // Only called after capture admission closes; this copy never competes
        // with an active tap's sample copy. Late callbacks return "closed".
        return CaptureSnapshot(sampleRate: sampleRate, samples: Array(storage.prefix(retained)),
            blocks: blocks, events: events, reasons: reasons, closed: closed)
    }
}

private extension Data {
    mutating func little<T: FixedWidthInteger>(_ value: T) {
        var encoded = value.littleEndian
        Swift.withUnsafeBytes(of: &encoded) { append(contentsOf: $0) }
    }
}

struct CaptureExport {
    static func wave(_ snapshot: CaptureSnapshot) throws -> Data {
        guard snapshot.closed, !snapshot.samples.isEmpty,
              snapshot.samples.count <= snapshot.sampleRate * 20 else { throw CaptureError.invalid("Invalid recording length") }
        let bytes = snapshot.samples.count * 4
        var data = Data(); data.reserveCapacity(bytes + 44)
        data.append(contentsOf: "RIFF".utf8); data.little(UInt32(36 + bytes)); data.append(contentsOf: "WAVEfmt ".utf8)
        data.little(UInt32(16)); data.little(UInt16(3)); data.little(UInt16(1))
        data.little(UInt32(snapshot.sampleRate)); data.little(UInt32(snapshot.sampleRate * 4))
        data.little(UInt16(4)); data.little(UInt16(32)); data.append(contentsOf: "data".utf8); data.little(UInt32(bytes))
        for sample in snapshot.samples {
            guard sample.isFinite else { throw CaptureError.invalid("Nonfinite sample in export") }
            data.little(sample.bitPattern)
        }
        return data
    }
    static func sha256(_ bytes: Data) -> String { SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined() }
    static func crc32(_ data: Data) -> UInt32 {
        var crc: UInt32 = 0xffffffff
        for byte in data {
            crc ^= UInt32(byte)
            for _ in 0..<8 { crc = (crc >> 1) ^ ((crc & 1) == 1 ? 0xedb88320 : 0) }
        }
        return crc ^ 0xffffffff
    }
    /// ZIP32 stored entries, no paths/directories or external archiver dependency.
    static func zip(wave: Data, manifest: Data) throws -> Data {
        guard manifest.count <= 1_048_576, wave.count + manifest.count <= 64 * 1024 * 1024 else {
            throw CaptureError.invalid("Export resource limit exceeded")
        }
        var output = Data(); var central = Data()
        for (name, payload) in [("recording.wav", wave), ("manifest.json", manifest)] {
            let filename = Data(name.utf8), checksum = crc32(payload), offset = UInt32(output.count), size = UInt32(payload.count)
            output.little(UInt32(0x04034b50)); output.little(UInt16(20)); output.little(UInt16(0)); output.little(UInt16(0))
            output.little(UInt16(0)); output.little(UInt16(33)); output.little(checksum); output.little(size); output.little(size)
            output.little(UInt16(filename.count)); output.little(UInt16(0)); output.append(filename); output.append(payload)
            central.little(UInt32(0x02014b50)); central.little(UInt16(20)); central.little(UInt16(20)); central.little(UInt16(0)); central.little(UInt16(0))
            central.little(UInt16(0)); central.little(UInt16(33)); central.little(checksum); central.little(size); central.little(size)
            central.little(UInt16(filename.count)); central.little(UInt16(0)); central.little(UInt16(0)); central.little(UInt16(0)); central.little(UInt16(0)); central.little(UInt32(0)); central.little(offset); central.append(filename)
        }
        let centralOffset = UInt32(output.count); output.append(central)
        output.little(UInt32(0x06054b50)); output.little(UInt16(0)); output.little(UInt16(0)); output.little(UInt16(2)); output.little(UInt16(2)); output.little(UInt32(central.count)); output.little(centralOffset); output.little(UInt16(0))
        return output
    }
    static func package(snapshot: CaptureSnapshot, captureID: String, device: DeviceSnapshot,
                        source: SourceDeclaration, session: SessionSnapshot,
                        initial: RouteSnapshot, final: RouteSnapshot, timebase: HostTimebase) throws -> Data {
        let wav = try wave(snapshot)
        guard !captureID.isEmpty, captureID.count <= 80, timebase.numer > 0, timebase.denom > 0 else { throw CaptureError.invalid("Invalid capture identity or host timebase") }
        let manifest = CaptureManifest(capture_id: captureID, recording_sha256: sha256(wav),
            sample_rate_hz: snapshot.sampleRate, frame_count: snapshot.samples.count, device: device,
            source_declaration: source, session: session, route_initial: initial, route_final: final, host_timebase: timebase,
            continuity: ContinuitySnapshot(status: snapshot.reasons.isEmpty ? "complete" : "interrupted", reasons: snapshot.reasons, blocks: snapshot.blocks), events: snapshot.events)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try zip(wave: wav, manifest: encoder.encode(manifest))
    }
}
