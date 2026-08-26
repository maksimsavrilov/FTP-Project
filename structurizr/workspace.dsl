workspace "Hosting Control System" "Distributed hosting management system" {

    model {

        // ============================================================
        // People
        // ============================================================

        admin = person "Admin" {
            description "Manages the whole hosting infrastructure"
        }

        reseller = person "Reseller" {
            description "Manages users and subscriptions within assigned limits"
        }

        siteUser = person "Site User" {
            description "Manages own hosting services"
        }


        // ============================================================
        // Main system
        // ============================================================

        hosting = softwareSystem "Hosting Control System" {

            // --------------------------------------------------------
            // Control plane
            // --------------------------------------------------------

            cli = container "CLI" {
                description "Unix-style command line interface"
                technology "Python"
            }

            master = container "Master Application" {
                description "Control plane, REST API, business logic, scheduling and reconciliation"
                technology "Python / FastAPI"
            }

            database = container "State Database" {
                description "Stores users, subscriptions, service plans, resources, nodes, services and desired state"
                technology "PostgreSQL"
            }


            // --------------------------------------------------------
            // Worker agents
            // --------------------------------------------------------

            webAgent = container "Web Agent" {
                description "Manages web hosting services"
                technology "Python"
            }

            dnsAgent = container "DNS Agent" {
                description "Manages DNS services"
                technology "Python"
            }

            mailAgent = container "Mail Agent" {
                description "Manages mail services"
                technology "Python"
            }

            dbAgent = container "DB Agent" {
                description "Manages database services"
                technology "Python"
            }
        }


        // ============================================================
        // User -> CLI
        // ============================================================

        admin -> cli "Uses"
        reseller -> cli "Uses"
        siteUser -> cli "Uses"


        // ============================================================
        // CLI -> Master
        // ============================================================

        cli -> master "Executes commands via REST/HTTP"


        // ============================================================
        // Master -> State DB
        // ============================================================

        master -> database "Reads and writes desired state"


        // ============================================================
        // Master -> Agents
        // ============================================================

        master -> webAgent "Controls and sends desired state via REST/HTTP"
        webAgent -> master "Reports actual state and heartbeat via REST/HTTP"

        master -> dnsAgent "Controls and sends desired state via REST/HTTP"
        dnsAgent -> master "Reports actual state and heartbeat via REST/HTTP"

        master -> mailAgent "Controls and sends desired state via REST/HTTP"
        mailAgent -> master "Reports actual state and heartbeat via REST/HTTP"

        master -> dbAgent "Controls and sends desired state via REST/HTTP"
        dbAgent -> master "Reports actual state and heartbeat via REST/HTTP"


        // ============================================================
        // Deployment model
        // ============================================================

        deploymentEnvironment "Production" {

            deploymentNode "Master Node" {

                masterInstance = containerInstance master
                databaseInstance = containerInstance database
            }


            deploymentNode "Worker Node" {

                webAgentInstance = containerInstance webAgent
                dnsAgentInstance = containerInstance dnsAgent
                mailAgentInstance = containerInstance mailAgent
            }


            deploymentNode "Database Worker Node" {

                dbAgentInstance = containerInstance dbAgent
            }
        }
    }


    // ================================================================
    // Views
    // ================================================================

    views {

        // ------------------------------------------------------------
        // Level 1 — System Context
        // ------------------------------------------------------------

        systemContext hosting "SystemContext" {
            include admin
            include reseller
            include siteUser
            include hosting
            autolayout lr
        }


        // ------------------------------------------------------------
        // Level 2 — Containers
        // ------------------------------------------------------------

        container hosting "Containers" {
            include *
            autolayout lr
        }


        // ------------------------------------------------------------
        // Deployment
        // ------------------------------------------------------------

        deployment hosting "Production" {
            include *
            autolayout lr
        }


        // ============================================================
        // Styles
        // ============================================================

        styles {

            element "Person" {
                shape person
                background "#08427b"
                color "#ffffff"
            }

            element "Software System" {
                background "#1168bd"
                color "#ffffff"
            }

            element "Container" {
                background "#438dd5"
                color "#ffffff"
            }

            element "Deployment Node" {
                background "#999999"
                color "#ffffff"
            }
        }
    }
}