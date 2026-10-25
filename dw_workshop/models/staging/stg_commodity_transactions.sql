with transactions_source as (
    select
        transaction_id,
        transaction_date,
        symbol,
        action,
        quantity,
        unit_price,
        broker
    from {{ ref('commodity_transactions') }}
),

formatted as (
    select
        trim(transaction_id) as transaction_id,
        cast(transaction_date as date) as transaction_date,
        trim(symbol) as symbol,
        case
            when trim(symbol) = 'CL=F' then 'Crude Oil (WTI)'
            when trim(symbol) = 'GC=F' then 'Gold'
            when trim(symbol) = 'SI=F' then 'Silver'
            else trim(symbol)
        end as commodity_name,
        upper(trim(action)) as action,
        cast(quantity as integer) as quantity,
        round(cast(unit_price as numeric), 4) as executed_unit_price,
        round(cast(quantity * unit_price as numeric), 2) as total_transaction_value,
        trim(broker) as broker
    from transactions_source
)

select * from formatted
