workspace "Hosting Control System" "Distributed hosting management system" {

    !identifiers hierarchical

    model {
        !include model/people.dsl

        hosting = softwareSystem "Hosting Control System" {
            !include model/cli.dsl
            !include model/master.dsl
            !include model/database.dsl
            !include model/agent-web.dsl
            !include model/agent-dns.dsl
            !include model/agent-mail.dsl
            !include model/agent-db.dsl
            
        }

        !include model/relations.dsl

        admin -> hosting.cli "Uses"
        reseller -> hosting.cli "Uses"
        siteUser -> hosting.cli "Uses"

        !include model/deployment.dsl
    }

    views {
        !include views/views.dsl
        !include views/styles.dsl
    }

    configuration {
        scope softwaresystem
    }

}
