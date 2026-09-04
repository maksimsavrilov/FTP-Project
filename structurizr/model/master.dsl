master = container "Master Application" {
    description "Control plane, REST API, business logic, scheduling and reconciliation"
    technology "Python / FastAPI"

    # API Components
    api = component "REST API" {
        description "HTTP API endpoints exposed to CLI and other clients"
        technology "FastAPI"
    }
    auth = component "Authentication & Authorization" {
        description "Authenticates users and authorizes operations"
        technology "Python"
    }

    # Domain Components
    users = component "User Management" {
        description "Manages Site Users and their lifecycle"
        technology "Python"
    }
    resellers = component "Reseller Management" {
        description "Manages Resellers and their users"
        technology "Python"
    }
    plans = component "Service Plan Management" {
        description "Manages service plans and resource limits hierarchy"
        technology "Python"
    }
    subscriptions = component "Subscription Management" {
        description "Manages user subscriptions, domains and their lifecycle"
        technology "Python"
    }
    services = component "Service Management" {
        description "Manages Web, DNS, Mail and DB services and their configuration"
        technology "Python"
    }
    resources = component "Resource Management" {
        description "Tracks resource allocation and limits"
        technology "Python"
    }
    nodes = component "Node Management" {
        description "Manages Worker Nodes, capabilities and health state"
        technology "Python"
    }

    # Control Plane Components
    scheduler = component "Scheduler" {
        description "Selects suitable Worker Nodes for services"
        technology "Python"
    }
    reconciliation = component "Reconciliation Manager" {
        description "Maintains desired state and reconciles it with Worker Agent actual state"
        technology "Python"
    }
    agentClient = component "Agent Client" {
        description "REST client used to communicate with Worker Agents"
        technology "Python / HTTP"
    }

    # Persistence Components
    repositories = component "Repositories" {
        description "Persistence layer for system state"
        technology "Python / SQLAlchemy"
    }

    # Relationships
    api -> auth "Authenticates and authorizes requests" "Python"
    api -> users "Manages users" "Python"
    api -> resellers "Manages resellers" "Python"
    api -> plans "Manages service plans" "Python"
    api -> subscriptions "Manages subscriptions" "Python"
    api -> services "Manages services" "Python"
    api -> resources "Manages resources" "Python"
    api -> nodes "Manages Worker Nodes" "Python"

    resellers -> users "Manages users belonging to reseller" "Python"
    plans -> subscriptions "Defines subscription limits" "Python"
    subscriptions -> services "Owns services" "Python"
    plans -> resources "Defines resource limits" "Python"
    subscriptions -> resources "Consumes resources" "Python"

    services -> scheduler "Requests service placement" "Python"
    nodes -> scheduler "Provides node capabilities and availability" "Python"
    scheduler -> nodes "Requests for node capabilities and availability" "Python"
    scheduler -> resources "Requests for available resources" "Python"
    resources -> scheduler "Provides resource availability" "Python"
    scheduler -> reconciliation "Creates or updates service assignment and desired state" "Python"

    reconciliation -> agentClient "Sends desired state and commands" "Python"
    agentClient -> reconciliation "Returns actual state and operation results" "Python / HTTP"
    reconciliation -> services "Updates service state" "Python / HTTP"

    users -> repositories "Persists user state" "SQLAlchemy"
    resellers -> repositories "Persists reseller state" "SQLAlchemy"
    plans -> repositories "Persists service plans" "SQLAlchemy"
    subscriptions -> repositories "Persists subscriptions" "SQLAlchemy"
    services -> repositories "Persists services and desired state" "SQLAlchemy"
    resources -> repositories "Persists resource allocation" "SQLAlchemy"
    nodes -> repositories "Persists node state" "SQLAlchemy"
    scheduler -> repositories "Reads assignments and resource state" "SQLAlchemy"
    reconciliation -> repositories "Reads and updates desired state" "SQLAlchemy"
}
