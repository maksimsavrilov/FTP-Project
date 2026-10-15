deploymentEnvironment "Production" {

    deploymentNode "Master Node" {
        masterInstance = containerInstance hosting.master
        databaseInstance = containerInstance hosting.database
    }

    deploymentNode "Authentication Node" {
       authServiceInstance = softwareSystemInstance authService
    }

    deploymentNode "Worker Node" {
        webBootstrap = infrastructureNode "Node-local Bootstrap" {
            description "Deploys and starts the Web service and Web Agent containers before registration"
            technology "Node provisioning"
        }
        webAgentInstance = containerInstance hosting.webAgent
        webServiceInstance = containerInstance hosting.webService
        dnsAgentInstance = containerInstance hosting.dnsAgent
        mailAgentInstance = containerInstance hosting.mailAgent

        apacheRuntimeAdapter = infrastructureNode "Apache Runtime Adapter" {
            description "Host-running Apache runtime adapter outside the Web Agent container"
            technology "systemd / httpd / apache"
            -> webAgentInstance "Shared Unix socket. Owns config files and daemon lifecycle"
        }

        webBootstrap -> webAgentInstance "Deploys and starts"
        webBootstrap -> webServiceInstance "Deploys and starts with shared Unix socket mount"
        webAgentInstance -> webServiceInstance "Reconciles Nginx through adapter over shared Unix socket"

        infrastructureNode bindRuntime "BIND" {
            description "DNS server managed by DNS Agent"
            technology "Bind DNS Server"
            -> dnsAgentInstance "Managed by"
        }

        infrastructureNode postfixRuntime "Postfix" {
            description "SMTP server managed by Mail Agent"
            technology "Postfix SMTP Server"
            -> mailAgentInstance "Managed by"
        }

        infrastructureNode qmailRuntime "Qmail" {
            description "SMTP server managed by Mail Agent"
            technology "Qmail SMTP Server"
            -> mailAgentInstance "Managed by"
        }
        
        infrastructureNode CourierRuntime "Courier" {
            description "IMAP server managed by Mail Agent"
            technology "Courier IMAP Server"
            -> mailAgentInstance "Managed by"
        }
    }

    deploymentNode "Database Worker Node" {
        dbAgentInstance = containerInstance hosting.dbAgent

        infrastructureNode mysqlRuntime "MySQL" {
            description "MySQL server managed by DB agent"
            technology "mysql"
            -> dbAgentInstance "Managed by"
        }

        infrastructureNode postgresqlRuntime "PostgreSQL" {
            description "PostgreSQL server managed by DB agent"
            technology "postgresql"
            -> dbAgentInstance "Managed by"
        }  
    }
}
