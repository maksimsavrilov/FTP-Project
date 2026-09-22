webAgent = container "Web Agent" {
    description "Manages web hosting services"
    technology "Python"

    webApi = component "REST API" {
        description "REST endpoints exposed to Master"
        technology "FastAPI"
    }
    webAuth = component "Authentication" {
        description "Validates requests from Master"
        technology "Python"
    }
    webDesiredState = component "Desired State Handler" {
        description "Accepts and validates desired state from Master"
        technology "Python"
    }
    webReconciliation = component "Reconciliation Engine" {
        description "Compares desired and actual state and determines required changes"
        technology "Python"
    }
    webProvider = component "Web Provider Adapter" {
        description "Translates desired web state and manages the selected local provider"
        technology "Python"
    }
    nginxProvider = component "Nginx Provider" {
        description "Generates, validates and applies Nginx configuration"
        technology "Python"
    }
    apacheProvider = component "Apache Provider" {
        description "Generates, validates and applies Apache configuration"
        technology "Python"
    }
    webStateReporter = component "State & Health Reporter" {
        description "Reports actual state, health and heartbeat to Master"
        technology "Python"
    }

    # ====================================================
    # Внутренние связи компонентов Web Agent (перенесены сюда)
    # ====================================================
    webApi -> webAuth "Authenticates Master requests" "Python"
    webApi -> webDesiredState "Accepts desired state" "Python"
    webDesiredState -> webReconciliation "Triggers reconciliation" "Python"
    webReconciliation -> webProvider "Applies required configuration" "Python"
    webProvider -> nginxProvider "Uses Nginx implementation" "Python"
    webProvider -> apacheProvider "Uses Apache implementation" "Python"
    webReconciliation -> webStateReporter "Reports reconciliation result" "Python"
    webStateReporter -> webApi "Exposes state and health information" "Python"
}
