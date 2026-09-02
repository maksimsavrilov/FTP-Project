deploymentEnvironment "Production" {

    deploymentNode "Master Node" {
        masterInstance = containerInstance hosting.master
        databaseInstance = containerInstance hosting.database
    }

    deploymentNode "Worker Node" {
        webAgentInstance = containerInstance hosting.webAgent
        dnsAgentInstance = containerInstance hosting.dnsAgent
        mailAgentInstance = containerInstance hosting.mailAgent

        infrastructureNode nginxRuntime "nginx" {
            description "Web server managed by Web Agent"
            technology "nginx"
            -> webAgentInstance "Managed by"
        }

        infrastructureNode apacheRuntime "Apache" {
            description "Web server managed by Web Agent"
            technology "Apache HTTP Server"
            -> webAgentInstance "Managed by"
        }

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
