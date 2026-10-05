// GOV.UK Frontend ships JavaScript without type declarations.
declare module "govuk-frontend" {
  class GovukComponent {
    constructor($root: Element, config?: Record<string, unknown>);
  }
  export class Button extends GovukComponent {}
  export class ExitThisPage extends GovukComponent {}
  export class NotificationBanner extends GovukComponent {}
  export class ServiceNavigation extends GovukComponent {}
  export class SkipLink extends GovukComponent {}
}
