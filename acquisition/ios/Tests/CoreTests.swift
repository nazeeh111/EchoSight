import Foundation
import Dispatch

func check(_ condition: @autoclosure () throws -> Bool, _ message: String) throws {
    if try condition() == false { throw CaptureError.invalid("TEST FAILED: " + message) }
}
func identityPackage(_ snapshot: CaptureSnapshot, _ id: String) throws -> Data {
    let route = RouteSnapshot(input_port_type: "injected_test", input_port_name: "No microphone used", input_channel_count: 1, input_sample_rate_hz: snapshot.sampleRate)
    return try CaptureExport.package(snapshot: snapshot, captureID: id,
        device: DeviceSnapshot(model: "injected-buffer-test", os_version: "not-a-phone-measurement"),
        source: SourceDeclaration(configuration_id: "synthetic-test", probe_id: "supplied-fixture", route_id: "no-physical-playback"),
        session: SessionSnapshot(category: "record", mode: "measurement", preferred_sample_rate_hz: 48000, activated_sample_rate_hz: snapshot.sampleRate),
        initial: route, final: route, timebase: HostTimebase(numer: 1, denom: 1))
}
func word(_ data: Data, _ index: Int) -> UInt32 {
    (0..<4).reduce(UInt32(0)) { $0 | (UInt32(data[index + $1]) << UInt32(8 * $1)) }
}

@main struct CoreTests {
    static func main() throws {
        let directory = URL(fileURLWithPath: CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "build/fixtures", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let samples: [Float] = [0, -0.0, Float.leastNonzeroMagnitude, Float(sign: .plus, exponent: -35, significand: 1), 0.12345678, -0.9876543, 0.5]
        let collector = try CaptureCollector(sampleRate: 48000)
        try check(collector.append(Array(samples[0..<4]), sampleRate: 48000, sampleTime: -100, hostTime: 1_000_000) == nil, "first exact block")
        try check(collector.append(Array(samples[4...]), sampleRate: 48000, sampleTime: -96, hostTime: 1_083_333) == nil, "partial final block")
        do { _ = try collector.snapshot(); throw CaptureError.invalid("Snapshot should reject active capture") } catch CaptureError.invalid(let message) { try check(message.contains("Stop capture"), "active export rejected") }
        collector.finish("user_stop")
        let snapshot = try collector.snapshot(), wave = try CaptureExport.wave(snapshot)
        try check(snapshot.samples.map(\.bitPattern) == samples.map(\.bitPattern), "Float32 bits preserved")
        try check(samples.indices.allSatisfy { word(wave, 44 + 4 * $0) == samples[$0].bitPattern }, "WAV exact Float32 payload")
        try check(word(wave, 24) == 48000 && word(wave, 40) == UInt32(4 * samples.count), "WAV counts/rate")
        try identityPackage(snapshot, "exact-float32-test").write(to: directory.appendingPathComponent("exact.echosight.zip"))
        try check(collector.append([0.1], sampleRate: 48000, sampleTime: -93, hostTime: 3_000_000) == "closed", "late buffer rejected")
        try check(try collector.snapshot().samples.count == samples.count, "export remains immutable")

        var encodingAttempts = 0, writeAttempts = 0
        var writePayloads: [Data] = []
        let pending = CapturePendingSave(encode: {
            encodingAttempts += 1
            if encodingAttempts == 1 { throw CaptureError.invalid("Injected encode failure") }
            return try identityPackage(snapshot, "retry-test")
        }, persist: { payload in
            writeAttempts += 1; writePayloads.append(payload)
            if writeAttempts == 1 { throw CaptureError.invalid("Injected disk failure") }
            let target = directory.appendingPathComponent("retry.echosight.zip")
            try payload.write(to: target, options: [.atomic]); return target
        })
        for expected in ["Injected encode failure", "Injected disk failure"] {
            do { _ = try pending.attempt(); throw CaptureError.invalid("Expected failure") }
            catch CaptureError.invalid(let message) { try check(message == expected, "save failure surfaced") }
        }
        let retried = try pending.attempt()
        try check(encodingAttempts == 2 && writeAttempts == 2 && writePayloads[0] == writePayloads[1], "retry reuses exact encoded bytes")
        try check(try Data(contentsOf: retried) == writePayloads[0], "retried durable save preserves evidence")

        for (name, sampleTime, hostTime) in [("gap", Int64(9), UInt64(2)), ("overlap", Int64(7), UInt64(2)), ("host-regression", Int64(8), UInt64(1))] {
            let c = try CaptureCollector(sampleRate: 48000)
            _ = c.append([0.1, 0.2], sampleRate: 48000, sampleTime: 6, hostTime: 1)
            try check(c.append([0.3], sampleRate: 48000, sampleTime: sampleTime, hostTime: hostTime) == "timestamp_invalid", name)
            let s = try c.snapshot(); try check(!s.reasons.isEmpty && s.samples.count == 3, "invalid clock bytes preserved")
            try identityPackage(s, name + "-test").write(to: directory.appendingPathComponent(name + ".echosight.zip"))
        }
        let invalid = try CaptureCollector(sampleRate: 48000)
        try check(invalid.append([0.2], sampleRate: 48000, sampleTime: nil, hostTime: nil) == "timestamp_invalid", "missing timestamp")
        try check(try invalid.snapshot().blocks[0].sample_time == nil, "invalid time stays null")
        let invalidBlock = try JSONSerialization.jsonObject(with: JSONEncoder().encode(invalid.snapshot().blocks[0])) as! [String: Any]
        try check(invalidBlock["sample_time"] is NSNull && invalidBlock["host_time"] is NSNull, "invalid timestamp keys encode explicit JSON null")
        try identityPackage(invalid.snapshot(), "invalid-timestamp-test").write(to: directory.appendingPathComponent("invalid-timestamp.echosight.zip"))

        let inconsistent = try CaptureCollector(sampleRate: 48000)
        _ = inconsistent.append([Float](repeating: 0.1, count: 480), sampleRate: 48000, sampleTime: 0, hostTime: 1_000_000)
        try check(inconsistent.append([0.2], sampleRate: 48000, sampleTime: 480, hostTime: 21_000_000) == "timestamp_invalid", "monotonic host clock with wrong elapsed time")
        try identityPackage(inconsistent.snapshot(), "host-inconsistent-test").write(to: directory.appendingPathComponent("host-inconsistent.echosight.zip"))
        let coarse = try CaptureCollector(sampleRate: 48000, hostTimebase: HostTimebase(numer: 10000, denom: 1))
        try check(coarse.append([0.1], sampleRate: 48000, sampleTime: 0, hostTime: 1) == "timestamp_invalid", "coarse host ticks cannot qualify continuity")
        let scaled = try CaptureCollector(sampleRate: 48000, hostTimebase: HostTimebase(numer: 125, denom: 3))
        _ = scaled.append([Float](repeating: 0.1, count: 480), sampleRate: 48000, sampleTime: 0, hostTime: 9_000_000_000_000_000)
        try check(scaled.append([0.2], sampleRate: 48000, sampleTime: 480, hostTime: 9_000_000_000_240_000) == nil, "native fractional tick scale and large host values")
        let drift = try CaptureCollector(sampleRate: 48000)
        _ = drift.append([Float](repeating: 0.1, count: 10), sampleRate: 48000, sampleTime: 0, hostTime: 1_000_000)
        try check(drift.append([Float](repeating: 0.1, count: 10), sampleRate: 48000, sampleTime: 10, hostTime: 1_250_000) == nil, "small adjacent discrepancy inside conservative bound")
        try check(drift.append([0.1], sampleRate: 48000, sampleTime: 20, hostTime: 1_500_000) == "timestamp_invalid", "cumulative drift exceeds first-to-current bound")

        let bounded = try CaptureCollector(sampleRate: 8000, seconds: 1)
        try check(bounded.append([Float](repeating: 0.25, count: 8003), sampleRate: 8000, sampleTime: 0, hostTime: 1) == "duration_limit", "exact frame cap")
        let cap = try bounded.snapshot(); try check(cap.samples.count == 8000 && cap.blocks[0].frame_count == 8000 && cap.reasons.isEmpty, "bounded partial last block")
        let blocks = try CaptureCollector(sampleRate: 48000, maximumBlocks: 1)
        _ = blocks.append([0.1], sampleRate: 48000, sampleTime: 0, hostTime: 1)
        try check(blocks.append([0.2], sampleRate: 48000, sampleTime: 1, hostTime: 2) == "buffer_overrun", "metadata capacity")
        try check(try blocks.snapshot().samples.count == 1, "overflow not silently appended")

        for reason in ["interruption", "route_change", "engine_configuration_change", "media_services_lost", "media_services_reset", "capture_error"] {
            let c = try CaptureCollector(sampleRate: 48000)
            _ = c.append([0.1], sampleRate: 48000, sampleTime: 0, hostTime: 1)
            c.finish(reason, detail: "Injected control")
            try check(try c.snapshot().reasons.contains(reason), reason + " retained")
        }
        for bad in [Float.nan, Float.infinity, -Float.infinity] {
            let c = try CaptureCollector(sampleRate: 48000)
            _ = c.append([0.1], sampleRate: 48000, sampleTime: 0, hostTime: 1)
            try check(c.append([bad], sampleRate: 48000, sampleTime: 1, hostTime: 2) == "nonfinite_samples", "nonfinite rejected")
            try check(try c.snapshot().samples.count == 1, "prior finite sample preserved")
        }
        let format = try CaptureCollector(sampleRate: 48000)
        _ = format.append([0.1], sampleRate: 48000, sampleTime: 0, hostTime: 1)
        try check(format.append([0.2], sampleRate: 44100, sampleTime: 1, hostTime: 2) == "format_changed", "rate change")

        // Exercise admission/finish races with injected buffers, never an engine.
        for _ in 0..<50 {
            let c = try CaptureCollector(sampleRate: 48000)
            _ = c.append([0.1], sampleRate: 48000, sampleTime: 0, hostTime: 1)
            let group = DispatchGroup()
            group.enter(); DispatchQueue.global().async { _ = c.append([0.2], sampleRate: 48000, sampleTime: 1, hostTime: 2); group.leave() }
            group.enter(); DispatchQueue.global().async { c.finish("user_stop"); group.leave() }
            group.wait()
            let s = try c.snapshot(); try check(s.samples.count == s.blocks.reduce(0) { $0 + $1.frame_count }, "stop/append block accounting")
            let before = try CaptureExport.wave(s)
            _ = c.append([0.3], sampleRate: 48000, sampleTime: 2, hostTime: 3)
            try check(try CaptureExport.wave(c.snapshot()) == before, "stopped export cannot mutate")
        }

        // Optional externally generated Float32 waveform for backend integration.
        if CommandLine.arguments.count > 2 {
            let input = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[2]))
            guard input.count % 4 == 0 else { throw CaptureError.invalid("Fixture is not Float32-aligned") }
            let values = stride(from: 0, to: input.count, by: 4).map { Float(bitPattern: word(input, $0)) }
            let c = try CaptureCollector(sampleRate: 48000)
            var offset = 0
            while offset < values.count {
                let count = min(511, values.count - offset)
                let reason = c.append(Array(values[offset..<offset+count]), sampleRate: 48000, sampleTime: Int64(offset), hostTime: 1_000_000_000 + UInt64(offset) * 1_000_000_000 / 48000)
                offset += count
                if reason != nil { break }
            }
            c.finish("user_stop")
            try identityPackage(c.snapshot(), "synthetic-waveform-test").write(to: directory.appendingPathComponent("waveform.echosight.zip"))
        }
        print("PASS: exact Float32/WAV/ZIP, counts, timestamps, interruption transitions, limits, invalid samples, and 50 stop/append races. No microphone or AVAudioEngine runtime used.")
    }
}
