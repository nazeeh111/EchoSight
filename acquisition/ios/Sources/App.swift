import UIKit

@main final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = CaptureViewController(); window.makeKeyAndVisible(); self.window = window
        return true
    }
}

final class CaptureViewController: UIViewController {
    private let recorder = NativeRecorder()
    private let status = UILabel(), start = UIButton(type: .system), stop = UIButton(type: .system), export = UIButton(type: .system)
    private let retry = UIButton(type: .system)
    private let configuration = UITextField(), probe = UITextField(), route = UITextField()
    private var exportedURL: URL?
    override func viewDidLoad() {
        super.viewDidLoad(); view.backgroundColor = .systemBackground
        title = "EchoSight capture"
        status.numberOfLines = 0
        status.text = "Stationary mono audio capture. Delivered samples are preserved; raw ADC access and physical accuracy are not established."
        for (field, placeholder) in [(configuration, "Source configuration ID or unknown"), (probe, "Probe ID or unknown"), (route, "Source playback route ID or unknown")] {
            field.placeholder = placeholder; field.borderStyle = .roundedRect; field.autocapitalizationType = .none; field.autocorrectionType = .no
        }
        start.setTitle("Start", for: .normal); stop.setTitle("Stop", for: .normal); export.setTitle("Export saved capture", for: .normal)
        retry.setTitle("Retry save", for: .normal)
        stop.isEnabled = false; export.isEnabled = false; retry.isHidden = true
        start.addTarget(self, action: #selector(begin), for: .touchUpInside)
        stop.addTarget(self, action: #selector(end), for: .touchUpInside)
        export.addTarget(self, action: #selector(share), for: .touchUpInside)
        retry.addTarget(self, action: #selector(retrySave), for: .touchUpInside)
        let stack = UIStackView(arrangedSubviews: [status, configuration, probe, route, start, stop, retry, export])
        stack.axis = .vertical; stack.spacing = 16; stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)
        NSLayoutConstraint.activate([stack.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 20), stack.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -20), stack.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 24)])
        recorder.onState = { [weak self] text, recording, url in
            guard let self = self else { return }
            self.status.text = text; self.stop.isEnabled = recording
            // During permission/start/export work, Start stays disabled until
            // a terminal status or saved file arrives.
            self.start.isEnabled = !recording && (url != nil || text.hasPrefix("No export") || text.hasPrefix("Capture could not start") || text.hasPrefix("Microphone permission was denied"))
            self.retry.isHidden = !self.recorder.canRetrySave
            self.retry.isEnabled = self.recorder.canRetrySave
            for field in [self.configuration, self.probe, self.route] { field.isEnabled = self.start.isEnabled }
            if let url = url { self.exportedURL = url; self.export.isEnabled = true }
            else if recording { self.export.isEnabled = false }
        }
    }
    private func declared(_ field: UITextField) -> String {
        let value = (field.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        return value.isEmpty ? "unknown" : String(value.prefix(160))
    }
    @objc private func begin() {
        view.endEditing(true); start.isEnabled = false
        recorder.requestStart(source: SourceDeclaration(configuration_id: declared(configuration), probe_id: declared(probe), route_id: declared(route)))
    }
    @objc private func end() { recorder.stop() }
    @objc private func retrySave() { recorder.retrySave() }
    @objc private func share() {
        guard let url = exportedURL else { return }
        let sheet = UIActivityViewController(activityItems: [url], applicationActivities: nil)
        sheet.popoverPresentationController?.sourceView = export
        present(sheet, animated: true)
    }
}
