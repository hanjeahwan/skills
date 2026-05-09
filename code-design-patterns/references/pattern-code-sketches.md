# Pattern Code Sketches

Use this reference when the user asks for basic code references for a pattern that is not fully expanded in `code-reference.md`. These sketches are intentionally compact. Adapt names, module layout, error types, and test framework to the current repository.

Every code-sketch answer should include:

- the domain `contract`
- the concrete `variant` or wrapper roles
- the `composition root` or wiring point when applicable
- concrete `verification` scenarios or test names

## Table Of Contents

- `Code Coverage Map`: where to find code guidance for each pattern.
- `Factory Method`: product creation hook.
- `Prototype`: safe clone/copy contract.
- `Singleton`: narrow process-wide identity only.
- `Bridge`: split abstraction and implementation axes.
- `Composite`: uniform leaf/container operations.
- `Facade`: stable workflow entry point.
- `Flyweight`: shared immutable intrinsic state.
- `Iterator`: representation-hidden traversal.
- `Mediator`: directed workflow coordination.
- `Template Method`: stable algorithm skeleton with hooks.
- `Visitor`: operations over stable element structures.

## Code Coverage Map

| Pattern | Primary code reference |
|---|---|
| Factory Method | This file; `code-reference.md` Strategy + Factory section |
| Abstract Factory | `code-reference.md` Abstract Factory section |
| Builder | `code-reference.md` Builder section |
| Prototype | This file |
| Singleton | This file as cautionary narrow sketch |
| Adapter | `code-reference.md` Adapter + Facade section |
| Bridge | This file |
| Composite | This file |
| Decorator | `code-reference.md` Decorator and Proxy section |
| Facade | This file; `code-reference.md` Adapter + Facade section |
| Flyweight | This file |
| Proxy | `code-reference.md` Decorator and Proxy section |
| Chain of Responsibility | `code-reference.md` Chain section |
| Command | `code-reference.md` Command + Memento section |
| Iterator | This file |
| Mediator | This file |
| Memento | `code-reference.md` Command + Memento section |
| Observer | `code-reference.md` Observer section |
| State | `code-reference.md` State section |
| Strategy | `code-reference.md` Strategy + Factory section |
| Template Method | This file |
| Visitor | This file |

## Factory Method

Use when subclasses or configuration decide which product to create while clients use the product contract.

```ts
interface ExportWriter {
  write(rows: ReportRow[]): Promise<ExportFile>;
}

abstract class ExportJob {
  async run(rows: ReportRow[]): Promise<ExportFile> {
    const writer = this.createWriter();
    return writer.write(rows);
  }

  protected abstract createWriter(): ExportWriter;
}

class CsvExportJob extends ExportJob {
  protected createWriter(): ExportWriter {
    return new CsvExportWriter();
  }
}
```

Test: adding `JsonExportJob` should not change `ExportJob.run`.

## Prototype

Use when configured runtime templates should produce independent copies.

```ts
interface ReportTemplate {
  clone(): ReportTemplate;
  rename(name: string): void;
  render(data: ReportData): Promise<RenderedReport>;
}

class ConfiguredReportTemplate implements ReportTemplate {
  constructor(
    private name: string,
    private readonly sections: ReportSection[],
  ) {}

  clone(): ReportTemplate {
    return new ConfiguredReportTemplate(this.name, this.sections.map((section) => section.clone()));
  }

  rename(name: string): void {
    this.name = name;
  }

  async render(data: ReportData): Promise<RenderedReport> {
    return renderSections(this.name, this.sections, data);
  }
}
```

Test: mutating the clone does not mutate the source template.

## Singleton

Prefer dependency injection. Use a singleton only when one process-wide identity is part of the domain or runtime contract.

```ts
class ProcessClock {
  private static instance: ProcessClock | null = null;

  private constructor() {}

  static current(): ProcessClock {
    if (ProcessClock.instance === null) {
      ProcessClock.instance = new ProcessClock();
    }

    return ProcessClock.instance;
  }

  now(): Date {
    return new Date();
  }
}
```

Test: lifecycle, concurrency, and reset behavior are explicit. For business services, inject `Clock` instead.

## Bridge

Use when abstraction and implementation vary independently.

```ts
interface NotificationSender {
  send(message: NotificationMessage): Promise<void>;
}

class EmailSender implements NotificationSender {
  async send(message: NotificationMessage): Promise<void> {
    await sendEmail(message);
  }
}

abstract class Notification {
  constructor(protected readonly sender: NotificationSender) {}

  abstract deliver(userId: string): Promise<void>;
}

class BillingNotification extends Notification {
  async deliver(userId: string): Promise<void> {
    await this.sender.send({ userId, subject: "Billing update" });
  }
}
```

Test: add a new notification type and a new sender without multiplying subclasses.

## Composite

Use when clients should treat leaf and container nodes uniformly.

```ts
interface PricedItem {
  totalCents(): number;
}

class ProductItem implements PricedItem {
  constructor(private readonly priceCents: number) {}

  totalCents(): number {
    return this.priceCents;
  }
}

class BundleItem implements PricedItem {
  constructor(private readonly children: PricedItem[]) {}

  totalCents(): number {
    return this.children.reduce((total, child) => total + child.totalCents(), 0);
  }
}
```

Test: nested bundles and single products are priced through the same contract.

## Facade

Use when clients need one stable workflow over several subsystem calls.

```ts
class InvoiceCheckoutFacade {
  constructor(
    private readonly inventory: InventoryService,
    private readonly payments: PaymentService,
    private readonly invoices: InvoiceService,
  ) {}

  async checkout(request: CheckoutRequest): Promise<CheckoutReceipt> {
    await this.inventory.reserve(request.items);
    const payment = await this.payments.authorize(request.payment);
    return this.invoices.createReceipt(request, payment);
  }
}
```

Test: facade exposes workflow semantics, while subsystem behavior remains tested independently.

## Flyweight

Use only when repeated intrinsic state creates real memory pressure.

```ts
class IconGlyph {
  constructor(
    readonly name: string,
    readonly vectorPath: string,
  ) {}
}

class IconGlyphFactory {
  private readonly glyphs = new Map<string, IconGlyph>();

  get(name: string, vectorPath: string): IconGlyph {
    const existing = this.glyphs.get(name);

    if (existing) {
      return existing;
    }

    const glyph = new IconGlyph(name, vectorPath);
    this.glyphs.set(name, glyph);
    return glyph;
  }
}

interface RenderedIcon {
  glyph: IconGlyph;
  color: string;
  size: number;
}
```

Test: shared glyph data is immutable; extrinsic render state stays outside the flyweight.

## Iterator

Use when traversal should hide storage, paging, tree shape, or cursor mechanics.

```ts
interface AsyncIteratorLike<TItem> {
  next(): Promise<TItem | null>;
}

class PagedCustomerIterator implements AsyncIteratorLike<Customer> {
  private page = 0;
  private buffer: Customer[] = [];

  constructor(private readonly api: CustomerApi) {}

  async next(): Promise<Customer | null> {
    if (this.buffer.length === 0) {
      this.page += 1;
      this.buffer = await this.api.fetchPage(this.page);
    }

    return this.buffer.shift() ?? null;
  }
}
```

Test: client code consumes customers without knowing page size or cursor details.

## Mediator

Use when several components participate in one workflow and direct calls are becoming chaotic.

```ts
interface CheckoutMediator {
  paymentAuthorized(payment: PaymentResult): Promise<void>;
  inventoryFailed(reason: string): Promise<void>;
}

class CheckoutWorkflowMediator implements CheckoutMediator {
  constructor(
    private readonly orders: OrderService,
    private readonly notifications: NotificationService,
  ) {}

  async paymentAuthorized(payment: PaymentResult): Promise<void> {
    await this.orders.markPaid(payment.orderId);
    await this.notifications.sendPaymentReceipt(payment.orderId);
  }

  async inventoryFailed(reason: string): Promise<void> {
    await this.notifications.alertOperations(reason);
  }
}
```

Test: workflow rules are tested at mediator level; components do not call each other directly.

## Template Method

Use when a stable algorithm skeleton owns ordering and subclasses fill narrow hooks.

```ts
abstract class ImportJob {
  async run(file: ImportFile): Promise<ImportSummary> {
    const rows = await this.parse(file);
    const validRows = this.validate(rows);
    return this.persist(validRows);
  }

  protected abstract parse(file: ImportFile): Promise<ImportRow[]>;

  protected validate(rows: ImportRow[]): ImportRow[] {
    return rows.filter((row) => row.isValid);
  }

  protected abstract persist(rows: ImportRow[]): Promise<ImportSummary>;
}
```

Test: base job preserves step order; subclasses only customize approved hooks.

## Visitor

Use when a stable element structure needs new operations.

```ts
interface DocumentNode {
  accept(visitor: DocumentVisitor): Promise<void>;
}

interface DocumentVisitor {
  visitParagraph(node: ParagraphNode): Promise<void>;
  visitImage(node: ImageNode): Promise<void>;
}

class ParagraphNode implements DocumentNode {
  constructor(readonly text: string) {}

  async accept(visitor: DocumentVisitor): Promise<void> {
    await visitor.visitParagraph(this);
  }
}

class WordCountVisitor implements DocumentVisitor {
  count = 0;

  async visitParagraph(node: ParagraphNode): Promise<void> {
    this.count += node.text.split(/\s+/).filter((word) => word.length > 0).length;
  }

  async visitImage(): Promise<void> {
    return;
  }
}
```

Verification:

- `WordCountVisitor counts paragraph text and image alt text`: proves a visitor handles every current element type.
- `All visitors handle every DocumentNode variant`: fails when a new node type is added without updating visitors.
- `Visitor is not introduced while node types are still changing`: design review check; if new node types are expected frequently, keep behavior near nodes or use simpler functions until the structure stabilizes.
