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
    nginxRuntimeClient = component "Nginx Runtime Client" {
        description "Publishes, validates and inspects per-service Nginx configuration through the host runtime"
        technology "Python"
    }
    nginxProvider = component "Nginx Provider" {
        description "Generates and serializes per-service Nginx configuration for the runtime"
        technology "Python"
    }
    apacheRuntimeClient = component "Apache Runtime Client" {
        description "Publishes, validates and inspects per-service Apache configuration through the host runtime"
        technology "Python"
    }
    apacheProvider = component "Apache Provider" {
        description "Generates and serializes per-service Apache configuration for the runtime"
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
    webProvider -> nginxProvider "Generates per-service Nginx config" "Python"
    nginxProvider -> nginxRuntimeClient "Publishes and validates config through runtime" "Python"
    webProvider -> apacheProvider "Generates per-service Apache config" "Python"
    apacheProvider -> apacheRuntimeClient "Publishes and validates config through runtime" "Python"
    webReconciliation -> webStateReporter "Reports reconciliation result" "Python"
    webStateReporter -> webApi "Exposes state and health information" "Python"
}
