# Android Guidelines — housing-app

Codebase-specific conventions. The reviewer already knows standard Android/Kotlin/Hilt/Compose best practices — only project-specific patterns are listed here.

---

## Module Structure

Multi-module clean architecture with vertical feature slices:

```
android/
├── app/              # Application, MainActivity, DI entrypoint
├── core/             # Shared: analytics, CustomDispatchers, ErrorReporter, utils
├── network/          # Retrofit: ApiClient, NetworkSdk, RemoteSource, REST sealed interface
├── database/         # Room: HousingDatabase, DAOs, entities, migrations
├── reactApp/         # React Native bridge
├── buildLogic/       # Convention plugins, shared build config
├── gradle/           # Version catalogs (libs.versions.toml)
└── demand/           # Feature modules:
    └── <feature>/
        ├── data/         # RepoImpl, RemoteSource, DTOs, mappers, DI
        ├── domain/       # IRepo interface, use cases, domain models
        └── presentation/ # ViewModel, Compose screens, UiState/Event/Effect
```

**Layer rule:** `presentation → domain → data`. Never reverse. Core/shared modules never import from feature modules.

---

## Codebase-Specific Patterns

### 1. CustomDispatchers (HIGH if violated)

Never use `Dispatchers.IO`/`Main` directly. Inject `CustomDispatchers` for testability.

```kotlin
// ✅
viewModelScope.launch(dispatchers.io) { ... }

// ❌
viewModelScope.launch(Dispatchers.IO) { ... }
```

### 2. REST Sealed Interface for Network Calls

All network calls go through `RemoteSource` using the `REST` sealed interface. Never call `ApiClient` directly or create Retrofit instances manually.

```kotlin
// ✅ Feature RemoteSource wraps RemoteSource
class HomeRemoteSource @Inject constructor(private val remoteSource: RemoteSource) {
    fun getData(): Flow<Result<Failure, HomeDto>> =
        remoteSource.networkCall(dto = HomeDto::class.java, rest = REST.GET(url = endpoints.homeUrl))
}
```

### 3. Endpoint Holders (no hardcoded URLs)

URLs come from injected endpoint holder classes, never hardcoded strings.

### 4. Result<Failure, T> Pattern

Network operations return `Result<Failure, T>` — not nullable types, not raw exceptions.

```kotlin
sealed class Result<out L, out R> {
    data class Error(val error: Failure) : Result<Failure, Nothing>()
    data class Success<out R>(val data: R) : Result<Nothing, R>()
}
```

### 5. CancellationException Must Be Re-thrown (HIGH)

Any `catch (e: Exception)` block must re-throw `CancellationException` to preserve structured concurrency.

### 6. State Exposure Pattern

`MutableStateFlow` is always private with public `asStateFlow()`. Mutations use `.update { }` (thread-safe), never direct `.value =` assignment.

### 7. EventHandlerViewModel (MVI)

ViewModels extend `EventHandlerViewModel<EVENT>` with sealed event classes. One-time effects use `Channel` or `MutableSharedFlow`.

### 8. Use Cases as Intermediary

ViewModels inject use case facades (`XxxUseCases` data class), not repositories directly. Use cases take `Provider<IRepo>` for lazy loading.

### 9. Compose Navigation

Uses compose-destinations library: `@NavGraph`, `@Destination` annotations, `hiltViewModel()` for ViewModel creation, `collectAsStateWithLifecycle()` for state, effects in `LaunchedEffect(Unit)`.

### 10. ErrorReporter for Production Errors

Use `ErrorReporter.reportNonFatal()` (Sentry) for production errors. `Timber` for debug logging. Never `Log.e` in production paths. Never log PII (tokens, phone numbers, emails).

### 11. Room Conventions

- Write operations: `suspend fun`
- Reactive reads: `fun` returning `Flow<T>`
- Multi-step writes: must use `@Transaction`

### 12. Build Config

All dependency versions in `gradle/libs.versions.toml`. SDK versions from `GradleConfig`. Convention plugins in `buildLogic/`.

### 13. Testing

- `MainDispatcherRule` to set test dispatcher
- Mock `CustomDispatchers` to return test dispatcher
- Always `advanceUntilIdle()` after async events
- Always `unmockkObject()` singletons in `@After`

---

## Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Repo Interface | `I{Feature}Repo` | `IHomeRepo` |
| Repo Impl | `{Feature}RepoImpl` | `HomeRepoImpl` |
| RemoteSource | `{Feature}RemoteSource` | `HomeRemoteSource` |
| Use Case | `{Action}UseCase` | `LeadCreateUseCase` |
| Use Case Facade | `{Feature}UseCases` | `CrfUseCases` |
| DTO | `{Feature}{Type}Dto` | `LeadSuccessResponseDto` |
| UI State/Event/Effect | `{Feature}UiState` / `{Feature}Event` / `{Feature}Effect` | `CrfBottomSheetUiState` |

Packages: `com.locon.housing` (app), `com.locon.core`, `com.locon.network`, `com.locon.database`, `com.locon.<feature>.{data|domain|presentation}`, `com.locon.coreUI`.
