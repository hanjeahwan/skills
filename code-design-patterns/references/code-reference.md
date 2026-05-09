# Code Reference

Use this file when the user asks for code, implementation boundaries, refactor sketches, or examples. Treat snippets as starting structures, not copy-paste answers. Rename everything to the user's domain, match the repository's language, and verify library APIs from local source or official docs before coding.

The examples use TypeScript because it makes contracts explicit, but the same boundaries translate to Java, Kotlin, C#, Python, Go, or Ruby.

## Table Of Contents

- `Code Reference Workflow`: how to adapt snippets safely.
- `Strategy + Factory For Provider Logic`: provider, format, channel, and algorithm variation.
- `Abstract Factory For Compatible Product Families`: matched families of clients, verifiers, exporters, widgets, or repositories.
- `Adapter + Facade For Third-Party SDKs`: vendor isolation, request/response translation, and error normalization.
- `Command + Memento For Undoable Or Durable Actions`: undo, redo, audit, queues, and snapshots.
- `State For Lifecycle-Dependent Behavior`: lifecycle-specific behavior and transition matrices.
- `Observer For In-Process Notifications`: publisher/subscriber boundaries and delivery cautions.
- `Decorator And Proxy Around A Stable Contract`: caching, authorization, tracing, lazy loading, and wrapper order.
- `Builder For Validated Construction`: multi-step construction without invalid escaped objects.
- `Chain Of Responsibility For Ordered Policy Or Middleware`: ordered handlers, safe fallback, and short-circuit rules.
- `Test Contract Template`: shared tests for substitutable implementations.

## Code Reference Workflow

```text
┌──────────────────────┐
│ Identify code smell   │
│ or change pressure    │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Pick the closest      │
│ skeleton below        │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Rename to domain      │
│ language              │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Add contract tests    │
│ before migration      │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Move one caller at a  │
│ time                  │
└──────────────────────┘
```

## Strategy + Factory For Provider Logic

Use when repeated conditionals choose interchangeable behavior, such as payment providers, export formats, pricing algorithms, or notification channels.

```ts
type ProviderId = "stripe" | "adyen" | "invoice";

interface PaymentRequest {
  amountCents: number;
  currency: string;
  customerId: string;
}

interface PaymentResult {
  providerReference: string;
  status: "authorized" | "requires_action" | "failed";
}

interface PaymentProvider {
  authorize(request: PaymentRequest): Promise<PaymentResult>;
  refund(providerReference: string, amountCents: number): Promise<void>;
}

class StripePaymentProvider implements PaymentProvider {
  constructor(private readonly client: StripeClient) {}

  async authorize(request: PaymentRequest): Promise<PaymentResult> {
    const result = await this.client.authorizePayment({
      amountCents: request.amountCents,
      currency: request.currency,
      customerId: request.customerId,
    });

    return {
      providerReference: result.id,
      status: result.status,
    };
  }

  async refund(providerReference: string, amountCents: number): Promise<void> {
    await this.client.refundPayment({ providerReference, amountCents });
  }
}

class PaymentProviderRegistry {
  constructor(private readonly providers: Record<ProviderId, PaymentProvider>) {}

  get(providerId: ProviderId): PaymentProvider {
    const provider = this.providers[providerId];

    if (!provider) {
      throw new Error(`Unsupported payment provider: ${providerId}`);
    }

    return provider;
  }
}

class CheckoutService {
  constructor(private readonly paymentProviders: PaymentProviderRegistry) {}

  async checkout(providerId: ProviderId, request: PaymentRequest): Promise<PaymentResult> {
    return this.paymentProviders.get(providerId).authorize(request);
  }
}
```

Verification target:

- A contract test runs the same authorization/refund scenarios against every provider.
- Adding a provider changes composition code and provider tests, not checkout orchestration.
- Provider-specific errors are normalized before crossing the domain boundary.

## Abstract Factory For Compatible Product Families

Use when a provider/platform/tenant produces several related collaborators that must match each other.

```ts
interface PaymentClient {
  authorize(request: PaymentRequest): Promise<PaymentResult>;
}

interface WebhookVerifier {
  verify(headers: Headers, body: string): Promise<VerifiedWebhook>;
}

interface ReconciliationExporter {
  exportSince(since: Date): Promise<ExportFile>;
}

interface PaymentProviderFactory {
  createPaymentClient(): PaymentClient;
  createWebhookVerifier(): WebhookVerifier;
  createReconciliationExporter(): ReconciliationExporter;
}

class StripeProviderFactory implements PaymentProviderFactory {
  constructor(private readonly config: StripeConfig) {}

  createPaymentClient(): PaymentClient {
    return new StripePaymentClient(this.config);
  }

  createWebhookVerifier(): WebhookVerifier {
    return new StripeWebhookVerifier(this.config.webhookSecret);
  }

  createReconciliationExporter(): ReconciliationExporter {
    return new StripeReconciliationExporter(this.config);
  }
}

class PaymentProviderFactoryRegistry {
  constructor(private readonly factories: Record<ProviderId, PaymentProviderFactory>) {}

  forProvider(providerId: ProviderId): PaymentProviderFactory {
    const factory = this.factories[providerId];

    if (!factory) {
      throw new Error(`Unsupported payment provider: ${providerId}`);
    }

    return factory;
  }
}
```

Verification target:

- For each provider, the client, webhook verifier, and exporter are created from one factory.
- A mismatched family cannot be assembled by normal application code.
- Provider factory registration is the only place that knows concrete provider classes.

## Adapter + Facade For Third-Party SDKs

Use Adapter when vendor APIs leak into domain code. Add a Facade when callers need one stable workflow over several vendor calls.

```ts
interface ShipmentRequest {
  orderId: string;
  destination: PostalAddress;
  packageWeightGrams: number;
}

interface ShipmentLabel {
  trackingNumber: string;
  labelUrl: string;
}

interface ShippingGateway {
  createLabel(request: ShipmentRequest): Promise<ShipmentLabel>;
}

class VendorShippingAdapter implements ShippingGateway {
  constructor(private readonly vendorClient: VendorShippingClient) {}

  async createLabel(request: ShipmentRequest): Promise<ShipmentLabel> {
    try {
      const response = await this.vendorClient.labels.create({
        reference: request.orderId,
        grams: request.packageWeightGrams,
        address: toVendorAddress(request.destination),
      });

      return {
        trackingNumber: response.tracking_code,
        labelUrl: response.label_url,
      };
    } catch (error) {
      throw normalizeShippingError(error);
    }
  }
}

class ShippingService {
  constructor(private readonly shippingGateway: ShippingGateway) {}

  async purchaseLabel(request: ShipmentRequest): Promise<ShipmentLabel> {
    return this.shippingGateway.createLabel(request);
  }
}
```

Verification target:

- Domain code imports `ShippingGateway`, not vendor SDK types.
- Vendor error classes are translated into domain errors at the adapter boundary.
- Contract tests can run against a fake gateway and the real adapter with mocked SDK responses.

## Command + Memento For Undoable Or Durable Actions

Use Command when an operation needs identity, metadata, queueing, audit, retry, or undo. Add Memento when undo requires a private snapshot of the receiver's state.

```ts
interface Command {
  readonly name: string;
  execute(): Promise<CommandResult>;
  undo?(): Promise<void>;
}

interface CommandResult {
  changed: boolean;
}

class InsertTextCommand implements Command {
  readonly name = "insert_text";
  private previousSelection: SelectionSnapshot | null = null;

  constructor(
    private readonly editor: DocumentEditor,
    private readonly text: string,
  ) {}

  async execute(): Promise<CommandResult> {
    this.previousSelection = this.editor.captureSelection();
    this.editor.insertText(this.text);

    return { changed: true };
  }

  async undo(): Promise<void> {
    if (!this.previousSelection) {
      throw new Error("Cannot undo before command execution");
    }

    this.editor.restoreSelection(this.previousSelection);
    this.editor.deletePreviousText(this.text.length);
  }
}

class CommandHistory {
  private readonly undoStack: Command[] = [];
  private readonly redoStack: Command[] = [];

  async run(command: Command): Promise<void> {
    const result = await command.execute();

    if (result.changed) {
      this.undoStack.push(command);
      this.redoStack.length = 0;
    }
  }

  async undo(): Promise<void> {
    const command = this.undoStack.pop();

    if (!command?.undo) {
      return;
    }

    await command.undo();
    this.redoStack.push(command);
  }
}
```

Verification target:

- Commands that do not change state are not added to history.
- Undo cannot run before execution.
- Commands intended for queues have serialization, idempotency, and permission tests.

## State For Lifecycle-Dependent Behavior

Use State when many operations branch on the same lifecycle status and each status changes what actions are valid.

```ts
interface SubscriptionState {
  activate(context: Subscription): Promise<void>;
  pause(context: Subscription): Promise<void>;
  cancel(context: Subscription): Promise<void>;
}

class TrialingState implements SubscriptionState {
  async activate(context: Subscription): Promise<void> {
    context.transitionTo(new ActiveState());
  }

  async pause(): Promise<void> {
    throw new Error("Trial subscriptions cannot be paused");
  }

  async cancel(context: Subscription): Promise<void> {
    context.transitionTo(new CanceledState());
  }
}

class ActiveState implements SubscriptionState {
  async activate(): Promise<void> {
    return;
  }

  async pause(context: Subscription): Promise<void> {
    context.transitionTo(new PausedState());
  }

  async cancel(context: Subscription): Promise<void> {
    context.transitionTo(new CanceledState());
  }
}

class Subscription {
  constructor(private state: SubscriptionState) {}

  transitionTo(nextState: SubscriptionState): void {
    this.state = nextState;
  }

  activate(): Promise<void> {
    return this.state.activate(this);
  }

  pause(): Promise<void> {
    return this.state.pause(this);
  }

  cancel(): Promise<void> {
    return this.state.cancel(this);
  }
}
```

Verification target:

- A transition table covers every state/action pair.
- Invalid actions fail with domain-specific errors.
- Persistence stores stable state identifiers, not class names.

## Observer For In-Process Notifications

Use Observer for independent in-process subscribers. If delivery, retries, durability, or cross-service communication matter, use the project's event bus or queue abstraction instead.

```ts
interface DomainEvent {
  readonly type: string;
  readonly occurredAt: Date;
}

interface EventSubscriber<TEvent extends DomainEvent> {
  handle(event: TEvent): Promise<void>;
}

class DomainEventPublisher<TEvent extends DomainEvent> {
  private readonly subscribers: EventSubscriber<TEvent>[] = [];

  subscribe(subscriber: EventSubscriber<TEvent>): void {
    this.subscribers.push(subscriber);
  }

  async publish(event: TEvent): Promise<void> {
    for (const subscriber of this.subscribers) {
      await subscriber.handle(event);
    }
  }
}
```

Verification target:

- Publisher does not import concrete subscribers.
- Subscriber failure semantics are explicit: stop, continue, collect errors, or retry.
- Critical workflows do not rely on best-effort in-process notifications.

## Decorator And Proxy Around A Stable Contract

Use Decorator for optional behavior layers. Use Proxy for access control, caching, lazy loading, remote calls, or audit around a subject.

```ts
interface ReportRenderer {
  render(request: ReportRequest): Promise<RenderedReport>;
}

class PdfReportRenderer implements ReportRenderer {
  async render(request: ReportRequest): Promise<RenderedReport> {
    return renderPdf(request);
  }
}

class CachedReportRenderer implements ReportRenderer {
  constructor(
    private readonly inner: ReportRenderer,
    private readonly cache: ReportCache,
  ) {}

  async render(request: ReportRequest): Promise<RenderedReport> {
    const cacheKey = reportCacheKey(request);
    const cached = await this.cache.get(cacheKey);

    if (cached) {
      return cached;
    }

    const rendered = await this.inner.render(request);
    await this.cache.set(cacheKey, rendered);

    return rendered;
  }
}

class AuthorizedReportRenderer implements ReportRenderer {
  constructor(
    private readonly inner: ReportRenderer,
    private readonly policy: ReportPolicy,
  ) {}

  async render(request: ReportRequest): Promise<RenderedReport> {
    await this.policy.assertCanRender(request.userId, request.reportId);
    return this.inner.render(request);
  }
}
```

Verification target:

- Wrapper order is assembled in one composition boundary.
- Contract tests pass against the base renderer and each wrapper stack.
- Cache keys include tenant, authorization-relevant inputs, and format.

## Builder For Validated Construction

Use Builder when object construction is multi-step and invalid intermediate states must not escape.

```ts
interface InvoiceDraft {
  customerId: string;
  lineItems: InvoiceLineItem[];
  dueDate: Date;
}

class InvoiceBuilder {
  private customerId: string | null = null;
  private readonly lineItems: InvoiceLineItem[] = [];
  private dueDate: Date | null = null;

  forCustomer(customerId: string): this {
    this.customerId = customerId;
    return this;
  }

  addLineItem(lineItem: InvoiceLineItem): this {
    this.lineItems.push(lineItem);
    return this;
  }

  dueOn(dueDate: Date): this {
    this.dueDate = dueDate;
    return this;
  }

  build(): InvoiceDraft {
    if (!this.customerId) {
      throw new Error("Invoice requires a customer");
    }

    if (this.lineItems.length === 0) {
      throw new Error("Invoice requires at least one line item");
    }

    if (!this.dueDate) {
      throw new Error("Invoice requires a due date");
    }

    return {
      customerId: this.customerId,
      lineItems: [...this.lineItems],
      dueDate: this.dueDate,
    };
  }
}
```

Verification target:

- Missing required fields fail at build time.
- Built objects cannot be mutated through builder internals.
- Fluent methods do not hide validation side effects.

## Chain Of Responsibility For Ordered Policy Or Middleware

Use when several handlers may accept, reject, or pass a request in a known order.

```ts
interface ApprovalRequest {
  amountCents: number;
  requesterId: string;
}

interface ApprovalHandler {
  handle(request: ApprovalRequest): Promise<ApprovalDecision | null>;
}

class ApprovalChain {
  constructor(private readonly handlers: ApprovalHandler[]) {}

  async decide(request: ApprovalRequest): Promise<ApprovalDecision> {
    for (const handler of this.handlers) {
      const decision = await handler.handle(request);

      if (decision) {
        return decision;
      }
    }

    return { status: "manual_review", reason: "No approval handler accepted the request" };
  }
}
```

Verification target:

- Handler order is explicit and tested.
- Unhandled requests have a safe fallback.
- Handler side effects are avoided or made idempotent.

## Test Contract Template

Use shared contract tests when multiple implementations must be substitutable.

```ts
interface PaymentProviderContractSubject {
  name: string;
  createProvider(): PaymentProvider;
}

function runPaymentProviderContract(subject: PaymentProviderContractSubject): void {
  describe(`${subject.name} PaymentProvider contract`, () => {
    it("authorizes a valid payment request", async () => {
      const provider = subject.createProvider();

      const result = await provider.authorize({
        amountCents: 2500,
        currency: "USD",
        customerId: "customer_123",
      });

      expect(typeof result.providerReference).toBe("string");
      expect(["authorized", "requires_action", "failed"]).toContain(result.status);
    });

    it("rejects unsupported refunds consistently", async () => {
      const provider = subject.createProvider();

      await expect(provider.refund("unknown_reference", 100)).rejects.toThrow();
    });
  });
}
```

Adapt this to the project's test framework and avoid implementation-specific assertions. Contract tests should prove caller expectations, not private branches.
