import AVFAudio
import UIKit
import Darwin

/// No playback, network service, voice processing, or background-recording mode.
final class NativeRecorder {
    var onState: ((String, Bool, URL?) -> Void)?
    private var engine: AVAudioEngine?
    private var collector: CaptureCollector?
    private var observers: [NSObjectProtocol] = []
    private var running = false
    private var exporting = false
    private var pendingSave: CapturePendingSave?
    private var savedStatus = ""
    var canRetrySave: Bool { pendingSave != nil && !exporting }
    private var source = SourceDeclaration(configuration_id: "unknown", probe_id: "unknown", route_id: "unknown")
    private var initialRoute: RouteSnapshot?
    private var sessionSnapshot: SessionSnapshot?
    private var captureID = ""
    private let encoderQueue = DispatchQueue(label: "EchoSight.capture.export", qos: .utility)

    init() {
        let center = NotificationCenter.default
        let notifications: [(Notification.Name, String)] = [
            (AVAudioSession.interruptionNotification, "interruption"),
            (AVAudioSession.routeChangeNotification, "route_change"),
            (AVAudioSession.mediaServicesWereLostNotification, "media_services_lost"),
            (AVAudioSession.mediaServicesWereResetNotification, "media_services_reset"),
            (.AVAudioEngineConfigurationChange, "engine_configuration_change"),
            (UIApplication.didEnterBackgroundNotification, "capture_error")
        ]
        for (name, event) in notifications {
            observers.append(center.addObserver(forName: name, object: nil, queue: .main) { [weak self] notification in
                guard let self = self, self.running else { return }
                self.stop(reason: event, detail: String(notification.name.rawValue.prefix(200)))
            })
        }
    }
    deinit { for observer in observers { NotificationCenter.default.removeObserver(observer) } }

    func requestStart(source: SourceDeclaration) {
        guard !running, !exporting, pendingSave == nil else { return }
        onState?("Requesting microphone permission", false, nil)
        // Called only by the user's Start button. Never invoked by tests/builds.
        AVAudioApplication.requestRecordPermission { [weak self] granted in
            DispatchQueue.main.async {
                guard let self = self else { return }
                guard granted else { self.onState?("Microphone permission was denied", false, nil); return }
                do { try self.start(source: source) }
                catch { self.onState?("Capture could not start: \(error)", false, nil) }
            }
        }
    }

    private func route(_ session: AVAudioSession) -> RouteSnapshot {
        let input = session.currentRoute.inputs.first
        return RouteSnapshot(input_port_type: String((input?.portType.rawValue ?? "unknown").prefix(160)),
            input_port_name: String((input?.portName ?? "unknown").prefix(160)),
            input_channel_count: session.inputNumberOfChannels,
            input_sample_rate_hz: Int(session.sampleRate.rounded()))
    }
    private func start(source: SourceDeclaration) throws {
        guard !running, !exporting, pendingSave == nil else { return }
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.record, mode: .measurement, options: [])
        try session.setPreferredSampleRate(48000)
        try session.setActive(true)
        do {
            try session.setPreferredInputNumberOfChannels(1)
            let newEngine = AVAudioEngine(), input = newEngine.inputNode
            let format = input.outputFormat(forBus: 0)
            guard session.category == .record, session.mode == .measurement,
                  session.sampleRate.rounded() == session.sampleRate,
                  format.commonFormat == .pcmFormatFloat32, format.channelCount == 1,
                  format.sampleRate.rounded() == format.sampleRate,
                  (8000...192000).contains(Int(format.sampleRate)), session.inputNumberOfChannels == 1 else {
                throw CaptureError.invalid("This input must deliver mono Float32 without channel conversion")
            }
            var timebase = mach_timebase_info_data_t(); mach_timebase_info(&timebase)
            let newCollector = try CaptureCollector(sampleRate: Int(format.sampleRate),
                hostTimebase: HostTimebase(numer: timebase.numer, denom: timebase.denom))
            initialRoute = route(session)
            sessionSnapshot = SessionSnapshot(category: session.category == .record ? "record" : session.category.rawValue, mode: session.mode == .measurement ? "measurement" : session.mode.rawValue, preferred_sample_rate_hz: Int(session.preferredSampleRate.rounded()),
                activated_sample_rate_hz: Int(session.sampleRate.rounded()))
            self.source = source; captureID = "ios-" + UUID().uuidString.lowercased()
            collector = newCollector; engine = newEngine
            input.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, timestamp in
                guard buffer.format.commonFormat == .pcmFormatFloat32,
                      buffer.format.channelCount == 1, let channel = buffer.floatChannelData?[0] else {
                    newCollector.finish("format_changed", detail: "Tap format changed or channel data disappeared")
                    DispatchQueue.main.async { self?.stop(reason: "format_changed", detail: "Unsupported tap format") }
                    return
                }
                let samples = UnsafeBufferPointer(start: channel, count: Int(buffer.frameLength))
                let stampRate = timestamp.isSampleTimeValid ? timestamp.sampleRate : buffer.format.sampleRate
                guard stampRate == buffer.format.sampleRate else {
                    newCollector.finish("format_changed", detail: "Tap and timestamp sample rates disagree")
                    DispatchQueue.main.async { self?.stop(reason: "format_changed", detail: "Timestamp rate mismatch") }
                    return
                }
                let reason = newCollector.append(samples, sampleRate: buffer.format.sampleRate,
                    sampleTime: timestamp.isSampleTimeValid ? timestamp.sampleTime : nil,
                    hostTime: timestamp.isHostTimeValid ? timestamp.hostTime : nil)
                if let reason = reason, reason != "closed" {
                    DispatchQueue.main.async { self?.stop(reason: reason, detail: "Collector stopped admission") }
                }
            }
            newEngine.prepare()
            try newEngine.start()
            running = true
            onState?("Recording at \(Int(format.sampleRate)) Hz. Keep the phone still and foregrounded.", true, nil)
        } catch {
            engine?.inputNode.removeTap(onBus: 0); engine?.stop(); engine = nil; collector = nil
            try? session.setActive(false)
            throw error
        }
    }

    func stop(reason: String = "user_stop", detail: String = "") {
        guard running, let collector = collector, let initial = initialRoute, let observedSession = sessionSnapshot else { return }
        running = false
        // Close admission first. An in-flight copy finishes under the collector
        // lock; any later callback returns closed. Export happens after this.
        collector.finish(reason, detail: detail)
        engine?.inputNode.removeTap(onBus: 0); engine?.stop(); engine = nil
        let session = AVAudioSession.sharedInstance(), finalRoute = route(session)
        if finalRoute != initial { collector.finish("route_change", detail: "Initial and final input routes differ") }
        try? session.setActive(false)
        let snapshot: CaptureSnapshot
        do { snapshot = try collector.snapshot() }
        catch { onState?("No export: \(error)", false, nil); return }
        var info = mach_timebase_info_data_t(); mach_timebase_info(&info)
        let timebase = HostTimebase(numer: info.numer, denom: info.denom)
        let device = DeviceSnapshot(model: UIDevice.current.model, os_version: UIDevice.current.systemVersion)
        let identity = captureID, source = self.source
        pendingSave = CapturePendingSave(encode: {
                try CaptureExport.package(snapshot: snapshot, captureID: identity, device: device,
                    source: source, session: observedSession, initial: initial, final: finalRoute, timebase: timebase)
            }, persist: { data in
                let documents = try FileManager.default.url(for: .documentDirectory, in: .userDomainMask, appropriateFor: nil, create: true)
                let directory = documents.appendingPathComponent("Captures", isDirectory: true)
                try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
                let url = directory.appendingPathComponent(identity + ".echosight.zip")
                try data.write(to: url, options: [.atomic])
                return url
            })
        savedStatus = snapshot.reasons.isEmpty ? "Complete recording saved; hardware fidelity remains unqualified." : "Interrupted recording saved: " + snapshot.reasons.joined(separator: ", ")
        retrySave()
    }

    func retrySave() {
        guard !running, !exporting, let job = pendingSave else { return }
        exporting = true; onState?("Saving original delivered samples and acquisition metadata", false, nil)
        encoderQueue.async { [weak self] in
            do {
                let url = try job.attempt()
                DispatchQueue.main.async {
                    guard let self = self else { return }
                    self.exporting = false; self.pendingSave = nil
                    self.onState?(self.savedStatus, false, url)
                }
            } catch {
                DispatchQueue.main.async {
                    self?.exporting = false
                    self?.onState?("Save failed; original capture retained in memory. Retry save before starting another capture: \(error)", false, nil)
                }
            }
        }
    }
}
