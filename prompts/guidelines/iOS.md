# iOS Development Guidelines - housing-app

This file contains iOS-specific conventions and patterns for the housing-app codebase.
**Last Updated:** Based on analysis of AppCore, Common, PDPModule, and HomePageModule.

## Dependency Injection (Container Pattern)

The codebase uses a custom `DIContainer` for dependency injection. **ALL** ViewControllers and ViewModels MUST be instantiated via `container.resolve()`.

### ✅ CORRECT - Use container.resolve()

**Example 1: ViewController + ViewModel with arguments**
```swift
// From PDPCoordinator.swift - openFloorPlanBottomSheet()
let vm = container.resolve(FloorPlanBottomSheetViewVMProtocol.self, arguments: data)
let vc = container.resolve(FloorPlanBottomSheetVC.self)
vc.viewModel = vm
presentBottomSheet(contentController: vc, style: .custom(600), type: .intrinsic, showPullBar: true)
```

**Example 2: Resolve with multiple arguments**
```swift
// From PDPDependencies.swift
container.registerFactory(PDPImmersiveViewModelProtocol.self) { args in
    guard let id = args[safe: 0] as? String,
          let type = args[safe: 1] as? PropertyTypes else {
        fatalError("Invalid arguments")
    }
    return PDPImmersiveViewModel(id: id, type: type, deps: deps)
}

// Usage:
let viewModel = container.resolve(PDPImmersiveViewModelProtocol.self, arguments: id, type)
```

**Example 3: Resolve ViewControllers**
```swift
// From PDPDependencies.swift
container.registerFactory(PDPViewController.self) {
    let vc = PDPViewController()
    return vc
}

// Usage:
let vc = container.resolve(PDPViewController.self)
```

### ❌ WRONG - Direct instantiation

**FOUND IN CODE REVIEW: PDPCoordinator.swift:364**
```swift
func openEMIBreakupBottomSheet(model: EMIBreakupBottomSheetModel, delegate: EMIBreakupBottomSheetVCDelegate?) {
    let vc = EMIBreakupBottomSheetVC()  // ❌ HIGH severity violation
    vc.model = model
    vc.delegate = delegate
    presentBottomSheet(contentController: vc, style: .custom(600), type: .intrinsic, showPullBar: true)
}
```

**SHOULD BE:**
```swift
func openEMIBreakupBottomSheet(model: EMIBreakupBottomSheetModel, delegate: EMIBreakupBottomSheetVCDelegate?) {
    let vm = container.resolve(EMIBreakupBottomSheetViewVMProtocol.self, arguments: model)  // ✅ Correct
    let vc = container.resolve(EMIBreakupBottomSheetVC.self)  // ✅ Correct
    vc.viewModel = vm
    vc.delegate = delegate
    presentBottomSheet(contentController: vc, style: .custom(600), type: .intrinsic, showPullBar: true)
}
```

**Why HIGH severity:**
- Violates the DI architecture used throughout the codebase
- Reduces testability (can't inject mock dependencies)
- Creates tight coupling
- Inconsistent with all other VC instantiations in PDPModule

---

## Memory Management

### ✅ CORRECT - Use [weak self] in closures

**Found throughout PDPModule:**
```swift
// From PDPCoordinator.swift
dismissBottomSheet(completion: { [weak self] in
    self?.presentSomeVC()
})

// From TopGalleryHeaderView.swift
delegate?.didTapTopGalleryHeaderSaveButton(addToFavorite: !isPropertySaved, fromLabel: PDPConstants.shortList) { [weak self] success in
    self?.updateUI(success)
}

// From SponsoredSellerView.swift
imageLoadTask = HousingImageManager.shared.loadImage(with: imageURL) { [weak self] image, _ in
    self?.imageView.image = image
}
```

### ❌ WRONG - Strong reference cycles
```swift
dismissBottomSheet(completion: {
    self.presentSomeVC()  // ❌ MEDIUM/HIGH severity - potential memory leak
})

HousingImageManager.shared.loadImage(with: url) { image, _ in
    self.imageView.image = image  // ❌ MEDIUM/HIGH severity - retain cycle
}
```

**Why:** Creates strong reference cycles, preventing proper deallocation of ViewControllers and memory leaks.

---

## Optional Handling

### ✅ CORRECT - Use guard or if-let
```swift
guard let value = optionalValue else { return }

if let value = optionalValue {
    // use value
}
```

### ❌ WRONG - Force unwrapping
```swift
let value = optionalValue!  // MEDIUM/HIGH severity - can crash
```

---

## Singleton Access

### ✅ CORRECT - Use .shared
```swift
let manager = DatabaseManager.shared
let analytics = AnalyticsManager.shared
```

### ❌ WRONG - Direct instantiation
```swift
let manager = DatabaseManager()  // HIGH severity violation
```

---

## Naming Conventions

### Classes/Structs/Protocols

**ViewControllers:**
- Format: `{Feature}ViewController` or `{Feature}VC`
- Examples from codebase:
  - `PDPViewController`
  - `PDPImmersiveViewController`
  - `FloorPlanBottomSheetVC`
  - `EMIBreakupBottomSheetVC`
  - `ScreenshotShareViewController`

**ViewModels:**
- Format: `{Feature}ViewModel` or `{Feature}VM`
- Examples:
  - `PDPImmersiveViewModel`
  - `PDPNPViewModel`
  - `FloorPlanBottomSheetViewVM`

**Protocols:**
- Format: `{Type}Protocol` or specific suffix like `Delegate`
- Examples from PDPModule:
  - `PDPViewModelProtocol`
  - `PDPNetworkServiceProtocol`
  - `FloorPlanBottomSheetViewVMProtocol`
  - `PDPCoordinatorDelegate`
  - `PDPCoordinatorBottomSheetProtocol`
  - `CRFSelectionViewProtocol`

**Coordinators:**
- Format: `{Module}Coordinator`
- Example: `PDPCoordinator`

### Variables/Functions
- Use `camelCase`
- Boolean properties: `isEnabled`, `hasData`, `canPerform`, `isPropertySaved`
- Function names: `openFloorPlanBottomSheet`, `dismissBottomSheet`, `presentBottomSheet`

### Constants
- Examples from codebase:
  - `DateFormat` (struct with static constants)
  - `BottomSheet` (configuration constants)
  - `PDPConstants` (module-specific constants)
  - Use structured constants in separate files (see AppCore/Constants/)

---

## Async Operations

### ✅ CORRECT - Use async/await
```swift
func fetchData() async throws -> Data {
    let data = try await networkService.fetch()
    return data
}
```

### ❌ WRONG - Old completion handlers (if codebase uses async/await)
```swift
func fetchData(completion: @escaping (Data?) -> Void) {
    // Only if codebase has migrated to async/await
}
```

---

## UI Updates

### ✅ CORRECT - Always on main thread
```swift
DispatchQueue.main.async {
    self.updateUI()
}

// Or with async/await
await MainActor.run {
    updateUI()
}
```

### ❌ WRONG - UI updates on background thread
```swift
updateUI()  // HIGH severity if called from background thread
```

---

## Error Handling

### ✅ CORRECT - Proper error propagation
```swift
func doSomething() throws {
    try performAction()
}

// Or
func doSomething() -> Result<Data, Error> {
    // implementation
}
```

### ❌ WRONG - Swallowing errors
```swift
try? performAction()  // MEDIUM severity - loses error context
```

---

## Code Organization

### Module Structure

The codebase follows a modular architecture:
```
ios/
├── AppCore/              # Core dependencies, networking, DI container
│   ├── DI/              # DIContainer.swift, CoreDependencies.swift
│   ├── Networking/      # NetworkService, Headers, Domains
│   ├── Constants/       # Global constants
│   └── Managers/        # Shared managers
├── Common/              # Shared models, protocols, utilities
│   ├── DI/              # CommonDependencies.swift
│   └── Constants/       # Shared constants
├── PDPModule/           # Property Detail Page module
│   ├── PDP/
│   │   ├── DI/          # PDPDependencies.swift (registers all PDP dependencies)
│   │   ├── Domain/      # Interactors, NetworkService
│   │   ├── Presentation/# ViewModels
│   │   ├── Views/       # Custom views, cells
│   │   └── PDPCoordinator.swift
└── HomePageModule/      # Similar structure
```

### Dependency Registration Pattern

Each module has a `{Module}Dependencies.swift` file that registers all dependencies:

```swift
// From PDPDependencies.swift
public final class PDPDependencies {
    public static func register(in container: DIContainer, analytics: AnalyticsLogging) {
        
        // Register ViewModels with protocols
        container.registerFactory(PDPImmersiveViewModelProtocol.self) { args in
            // Factory implementation
        }
        
        // Register ViewControllers
        container.registerFactory(PDPViewController.self) {
            let vc = PDPViewController()
            return vc
        }
        
        // Register Coordinators
        container.registerFactory(PDPCoordinatorProtocol.self) { args in
            return PDPCoordinator(container: container, id: id, type: type)
        }
    }
}
```

### File Size Guidelines
- Based on codebase analysis:
  - ViewControllers: Typically 200-500 lines
  - ViewModels: Split into extensions (e.g., `PDPViewModel+Tabs.swift`)
  - Complex ViewModels use protocol composition
  - Large files split using extensions with descriptive names

### Method Complexity
- Avoid > 3 levels of nesting
- Extract complex logic into private methods
- Use extensions to organize code by feature (see `PDPViewModel+AllianceBanner.swift`)

---

## Testing

### Required Tests
- All ViewModels must have unit tests
- Business logic must be tested
- Use dependency injection for testability

---

## Project-Specific Patterns

### Bottom Sheet Presentation Pattern

**✅ CORRECT - From PDPCoordinator.swift:**
```swift
func openFloorPlanBottomSheet(
    data: FloorPlanBottomSheetModel?,
    sheetViewLayout: NSCollectionLayoutSection,
    shareData: ShareData?,
    listingModel: BaseListingModelProtocol?,
    pdpModel: PDPModelProtocol?,
    selectedIndex: Int
) {
    guard let data = data else { return }
    let vm = container.resolve(FloorPlanBottomSheetViewVMProtocol.self, arguments: data)
    let vc = container.resolve(FloorPlanBottomSheetVC.self)
    vc.viewModel = vm
    vc.sheetViewLayout = sheetViewLayout
    vc.shareData = shareData
    vc.listingModel = listingModel
    vc.pdpModel = pdpModel
    vc.selectedIndex = selectedIndex
    presentBottomSheet(contentController: vc, style: .custom(600), type: .intrinsic, showPullBar: true)
}
```

**❌ WRONG - Direct instantiation:**
```swift
func openEMIBreakupBottomSheet(model: EMIBreakupBottomSheetModel, delegate: EMIBreakupBottomSheetVCDelegate?) {
    let vc = EMIBreakupBottomSheetVC()  // ❌ HIGH severity - violates DI pattern
    vc.model = model
    vc.delegate = delegate
    presentBottomSheet(contentController: vc, style: .custom(600), type: .intrinsic, showPullBar: true)
}
```

### Coordinator Pattern

The codebase uses coordinators to manage navigation:
- Each module has a `{Module}Coordinator`
- Coordinators hold references to `DIContainer`
- Navigation logic is delegated to coordinators
- ViewControllers should NOT perform navigation directly

**Example:**
```swift
// PDPCoordinator initialization
let coordinator = container.resolve(PDPCoordinatorProtocol.self, arguments: id, typeString, multiCardID)
```

### Protocol-Based Architecture

- ViewModels are accessed via protocols: `PDPViewModelProtocol`, not concrete types
- Network services use protocols: `PDPNetworkServiceProtocol`
- Benefits: Easier testing, loose coupling, dependency inversion

---

## Common Violations Found in Codebase

Based on analysis of housing-app (Jan 2026):

### 1. Direct ViewController Instantiation (HIGH Severity)
**Location:** `PDPCoordinator.swift:364`
```swift
❌ let vc = EMIBreakupBottomSheetVC()
✅ let vc = container.resolve(EMIBreakupBottomSheetVC.self)
```

### 2. Missing ViewModel Resolution
Many bottom sheet presentations skip ViewModel creation via DI.

**Pattern to follow:**
1. Resolve ViewModel with arguments: `container.resolve(VMProtocol.self, arguments: data)`
2. Resolve ViewController: `container.resolve(VC.self)`
3. Assign ViewModel to VC: `vc.viewModel = vm`
4. Present

---

## Notes for Reviewers

- **DI Pattern violations are HIGH severity** - they break the entire architecture
- **Memory management issues are HIGH severity** - they cause leaks
- **Convention violations are MEDIUM severity** - they affect maintainability
- Always reference this file in review comments with specific line numbers
- Update this file when new patterns are established or violations are found

---

## Access Modifiers

Always specify an access control modifier (`public`, `private`, `internal`, `fileprivate`). Assigning access modifiers affects dispatch mechanisms in Swift—static dispatch or dynamic dispatch.

### ✅ CORRECT - Use access modifiers
```swift
final class NetworkManager {
    private let apiKey = "12345" // Only accessible within this class

    func fetchData() {
        // Function accessible within module (default: internal)
    }
}
```

### ❌ WRONG - Missing access control
```swift
class NetworkManager {
    let apiKey = "12345" // No access control (could be modified from anywhere)

    func fetchData() {
        // No access modifier specified
    }
}
```

**Why:** Enhances encapsulation, improves security, and prevents unintended modifications.

---

## Function Parameter Formatting

When a function has more than three parameters, place each on a new line. Use `ctrl + m` in Xcode.

### ✅ CORRECT - Parameters on new lines
```swift
func fetchData(
    from url: URL,
    withHeaders headers: [String: String],
    usingCache cache: Bool,
    from url: URL,
    withHeaders: Bool,
    completion: @escaping (Result<Data, Error>) -> Void
) {
    // Implementation
}
```

### ❌ WRONG - All parameters on one line
```swift
func fetchData(from url: URL, withHeaders headers: [String: String], usingCache cache: Bool, from url: URL,
    withHeaders Bool, completion: @escaping (Result<Data, Error>) -> Void) {
}
```

**Why:** Improves readability and reduces horizontal scrolling.

---

## Constants

Keep all constants in a single file or inside an enum/struct. Avoid hardcoded values.

### ✅ CORRECT - Structured constants
```swift
struct API {
    static let baseURL = "https://api.example.com"
    static let timeoutInterval = 30.0
}
```

### ❌ WRONG - Hardcoded values
```swift
class NetworkManager {
    func fetchData() {
        let url = "https://api.example.com" // Hardcoded value
        let timeout = 30.0
    }
}
```

**Why:** Avoids hardcoded values and improves maintainability.

---

## Delegate Functions in Extensions

Keep delegate methods in a separate extension instead of mixing them within the main class. Larger extensions should be moved to new files.

### ✅ CORRECT - Delegates in extension
```swift
class MyViewController: UIViewController {
    private let tableView = UITableView()

    override func viewDidLoad() {
        super.viewDidLoad()
        tableView.delegate = self
    }
}

// MARK: - UITableViewDelegate
extension MyViewController: UITableViewDelegate {
    func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        print("Row selected")
    }
}
```

### ❌ WRONG - Delegates mixed in class body
```swift
class MyViewController: UIViewController, UITableViewDelegate {
    private let tableView = UITableView()

    override func viewDidLoad() {
        super.viewDidLoad()
        tableView.delegate = self
    }

    func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        print("Row selected")
    }
}
```

**Why:** Improves code organization, enhances readability, and separates concerns.

---

## Function Length

Break large functions into smaller, reusable functions. Functions should not exceed 40-50 lines.

### ✅ CORRECT - Small focused functions
```swift
func processUser() {
    validateUser()
    fetchUserData()
    updateUI()
}

private func validateUser() { /* Validation logic */ }
private func fetchUserData() { /* API calls */ }
private func updateUI() { /* Update UI */ }
```

### ❌ WRONG - Monolithic function
```swift
func processUser() {
    // Validation logic...
    // API calls...
    // UI updates...
}
```

**Why:** Improves readability, debugging, and unit testing.

---

## Nesting

Avoid excessive nested loops/conditions. Prefer combining conditions.

### ✅ CORRECT - Flat conditions
```swift
if isUserLoggedIn, hasPermissions, isSubscribed {
    showHomeScreen()
} else if !isUserLoggedIn {
    showLoginScreen()
}
```

### ❌ WRONG - Deep nesting
```swift
if isUserLoggedIn {
    if hasPermissions {
        if isSubscribed {
            showHomeScreen()
        }
    }
} else {
    showLoginScreen()
}
```

**Why:** Increases code readability and reduces complexity.

---

## Guard for Early Returns

Prefer `guard` to reduce indentation and improve readability.

### ✅ CORRECT - Guard early return
```swift
func processUser(user: User?) {
    guard let user else {
        print("No user found")
        return
    }

    print("Processing user: \(user.name)")
}
```

### ❌ WRONG - Nested if-else
```swift
func processUser(user: User?) {
    if let user {
        print("Processing user: \(user.name)")
        // logic for if user present
    } else {
        print("No user found")
    }
}
```

**Why:** Avoids pyramid of doom and makes code cleaner.

---

## Prefer struct Over class

Use `struct` unless you need inheritance or reference semantics.

### ✅ CORRECT - Value type
```swift
struct User {
    let name: String
    let age: Int
}
```

### ❌ WRONG - Reference type when not needed
```swift
class User {
    var name: String
    var age: Int

    init(name: String, age: Int) {
        self.name = name
        self.age = age
    }
}
```

**Why:** `struct` is faster, safer, and avoids unexpected side effects.

---

## File Size

Keep files under 500 lines. Split large files into smaller files or use extensions for organizing code.

---

## Lazy Initialization

Use `lazy var` when initialization is expensive and only needed on demand.

### ✅ CORRECT - Lazy initialization
```swift
class ProfileViewController: UIViewController {
    lazy var profileImageView: UIImageView = {
        let imageView = UIImageView()
        imageView.contentMode = .scaleAspectFit
        return imageView
    }()
}
```

### ❌ WRONG - Eager initialization
```swift
class ProfileViewController: UIViewController {
    let profileImageView = UIImageView()  // Created even if never used
}
```

**Why:** Improves performance by delaying object creation.

---

## Pull Request Size

Keep Pull Requests (PRs) small (preferably under 1500 lines). Separate UI updates and backend logic. Refactor bug fixes and feature updates into separate PRs.

**Why:** Easier for reviewers to understand and reduces merge conflicts.

---

## Assets, Labels & Colors

Always use existing colors and image assets from the asset catalog. Do not introduce new colors unless absolutely necessary. New images are allowed — use `.svg` for small images and `.heic` for large images.

### ✅ CORRECT - Use ColorAssets and ImageAssets

```swift
// Colors
ColorAssets.TextColors.white100.color

// Images
ImageAssets.activeSavedProperties.image
```

### ❌ WRONG - Hardcoded colors or plain UILabel

```swift
UIColor(red: 0.5, green: 0.5, blue: 0.5, alpha: 1.0)  // ❌ Use ColorAssets
UILabel()  // ❌ Use typed label classes like UILabel_12_400_16
```

**Guidelines:**
- Before introducing a new color, check for a visually matching color in `ColorAssets`. If no match is found, confirm with the design team before proceeding.
- Use `.svg` for small images (icons, logos) and `.heic` for large images (photos, backgrounds).
- Use naming conventions and folders aligned with feature/module structure.
- Always use typed label classes like `UILabel_12_400_16`. Do not use plain `UILabel`.

**Converting PNG to HEIC:**
```bash
# First, install ImageMagick:
brew install imagemagick

# Then convert PNG to HEIC:
convert inputImage.png -alpha on outputImage.heic
```

---

## Code Reusability

Reuse logic like filters, formatting, or URL prep wherever possible. Move repeated logic to utility methods, extensions, or helpers.

### ✅ CORRECT - Reusable utility
```swift
FilterUtils.applyOwnerFilter(to: &params)
```

### ❌ WRONG - Inline duplication
```swift
params["owner_type"] = "OWNER"  // ❌ Duplicated across multiple places
```

**Why:** Reduces duplication, improves readability & debugging, and is easier to maintain or update.

---

## Clean Code

Avoid unused variables, functions, or imports. Always remove unused `var`, `func`, and `import` statements before pushing your code.

**Why:** Reduces clutter, prevents confusion during debugging, and improves performance and readability.

---

## Prefer Delegates Over Callbacks

Use delegates instead of callbacks wherever applicable. Always declare delegates as `weak` to avoid retain cycles.

### ✅ CORRECT - Delegate pattern
```swift
protocol MyViewDelegate: AnyObject {
    func didTapAction()
}

class MyView: UIView {
    weak var delegate: MyViewDelegate?

    @IBAction func actionButtonTapped() {
        delegate?.didTapAction()
    }
}

class MyViewController: UIViewController, MyViewDelegate {
    func didTapAction() {
        // Handle action
    }

    func setupView() {
        myView.delegate = self
    }
}
```

### ❌ WRONG - Callback without weak reference
```swift
var onAction: (() -> Void)?  // ❌ Can cause retain cycles if not handled properly
```

**Why:** Improves separation of concerns, easier to scale and test, aligns with iOS best practices.

---

## Reusable Small Views

Structure your UI using small, reusable views. Create separate `UIView` subclasses for `UICollectionView`, separate `UICollectionViewCell` subclasses, and use model structs to pass data cleanly into views.

### ✅ CORRECT - Modular view structure
```swift
// MARK: - Model
struct UserModel {
    let name: String
    let age: Int
}

// MARK: - Cell
final class UserCell: UICollectionViewCell {
    func configure(with model: UserModel) {
        // Setup UI
    }
}

// MARK: - Reusable View with CollectionView
final class UserListView: BaseUIView, UICollectionViewDataSource {
    private var users: [UserModel] = []

    func setup(with models: [UserModel]) {
        self.users = models
        collectionView.reloadData()
    }

    func collectionView(_ collectionView: UICollectionView,
                        cellForItemAt indexPath: IndexPath) -> UICollectionViewCell {
        let cell = collectionView.dequeueReusableCell(withReuseIdentifier: "UserCell", for: indexPath) as! UserCell
        cell.configure(with: users[indexPath.item])
        return cell
    }
}
```

**Why:** Promotes modularity and testability, enhances readability and reusability, simplifies layout and logic isolation.

---

## Safe Array Access

Always check index bounds when accessing array elements using subscript. Use a safe subscript extension.

### ✅ CORRECT - Safe subscript
```swift
let parts = inputString.split(separator: "|")
let first = parts[safe: 0]  // ✅ Safe access
```

### ❌ WRONG - Direct index access
```swift
let first = parts[0]  // ❌ May crash if array is empty
```

**Why:** Prevents crashes due to out-of-bounds access and makes your code safer and more resilient.

---

## Localized Strings

Always use localized strings instead of hardcoded text.

### ✅ CORRECT - Use Localized keys
```swift
label.text = Localized.last1Year
```

### ❌ WRONG - Hardcoded strings
```swift
label.text = "Last 1 Year"  // ❌ Not localized
```

**How to Use:**
1. Search for your string in `Localizable.strings`.
2. If not found, add the new key and translation.
3. Use `Localized.<key>` syntax consistently for better discoverability and reuse.

**Why:** Supports multiple languages, improves maintainability and consistency across the app.

---

## Shorthand Code

Use shorthand Swift syntax wherever possible. Leverage `compactMap`, trailing closures, optional chaining, and shorthand bindings.

### ✅ CORRECT - Shorthand binding
```swift
guard let self else { return }
```

### ❌ WRONG - Verbose binding
```swift
guard let self = self else { return }
```

**Why:** Improves readability, reduces boilerplate, and utilizes Swift's powerful features.

---

## Quick Reference

**When reviewing a PR, check:**
1. ✅ All VCs/VMs use `container.resolve()` (not direct instantiation)
2. ✅ All closures capturing `self` use `[weak self]`
3. ✅ Optionals handled safely (guard/if-let, not force unwrap)
4. ✅ Naming follows conventions (Protocol suffix, VC/VM suffix)
5. ✅ Dependencies registered in `{Module}Dependencies.swift`
6. ✅ ViewModels accessed via protocols, not concrete types
7. ✅ Access modifiers assigned to all classes and properties
8. ✅ Functions ≤ 40-50 lines, files ≤ 500 lines
9. ✅ No hardcoded strings — use `Localized.<key>`
10. ✅ No hardcoded colors — use `ColorAssets`
11. ✅ Images use `.svg` (small) or `.heic` (large), accessed via `ImageAssets`
12. ✅ UILabels use typed label classes (e.g., `UILabel_12_400_16`)
13. ✅ Safe array access via `[safe:]` subscript
14. ✅ Delegates preferred over callbacks, declared `weak`
15. ✅ No unused variables, functions, or imports
16. ✅ PRs kept small (under 1500 lines)
17. ✅ Reusable small views for UI components
18. ✅ Shorthand Swift syntax used where possible
