dnsAgent = container "DNS Agent" {
    description "Manages DNS services"
    technology "Python"

    dnsApi = component "REST API" {
        description "REST endpoints exposed to Master"
        technology "FastAPI"
    }
    dnsAuth = component "Authentication" {
        description "Validates requests from Master"
        technology "Python"
    }
    dnsDesiredState = component "Desired State Handler" {
        description "Accepts and validates desired DNS state from Master"
        technology "Python"
    }
    dnsReconciliation = component "Reconciliation Engine" {
        description "Compares desired DNS state with actual state"
        technology "Python"
    }
    dnsConfig = component "DNS Configuration Manager" {
        description "Manages DNS Agent configuration"
        technology "Python"
    }
    zoneManager = component "Zone Manager" {
        description "Creates, updates and removes DNS zones and records"
        technology "Python"
    }
    bindManager = component "BIND Manager" {
        description "Manages BIND configuration, validation and lifecycle"
        technology "Python"
    }
    dnsStateReporter = component "State & Health Reporter" {
        description "Reports actual DNS state, health and heartbeat to Master"
        technology "Python"
    }

    # Relationships
    dnsApi -> dnsAuth "Authenticates Master requests" "Python"
    dnsApi -> dnsDesiredState "Accepts desired DNS state" "Python"
    dnsDesiredState -> dnsReconciliation "Triggers reconciliation" "Python"
    dnsReconciliation -> dnsConfig "Applies required DNS configuration" "Python"
    dnsConfig -> zoneManager "Manages zones and records" "Python"
    zoneManager -> bindManager "Applies BIND configuration" "Python"
    dnsReconciliation -> dnsStateReporter "Reports reconciliation result" "Python"
    dnsStateReporter -> dnsApi "Exposes state and health information" "Python"
}
