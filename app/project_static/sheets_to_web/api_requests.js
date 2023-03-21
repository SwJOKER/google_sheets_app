    async function status_request() {
        let url = SHEET_API_URL + SHEET_KEY
        let response = await fetch(url)
        if (response.status === 200) {
            let sheet = await response.json()
            return sheet
        }
    }

    async function check_status() {
        console.log('check')
        await new Promise(resolve => setTimeout( () => {
            init_update_page()
        }, 5000))
    }

    async function get_orders() {
        let url = SHEET_API_URL + SHEET_KEY + '?full=1'
        let response = await fetch(url)
        if (response.status === 200) {
            let sheet = await response.json()
            let orders = sheet['orders']
            return orders
        }
    }

    async function update_page(){
        let orders = await get_orders()
        let current_orders = []
        let new_orders = []
        $('table').find('tr').each(function(){ if (this.id) {current_orders.push(this.id)}})
        console.log('start')
        orders.forEach(function(order){
            console.log(order['raw_index'])
            let order_index = order['order_index']
            let elem = $('table').find(`tr[id=${order_index}]`).find('td').each(function(){
              //  console.log(this.id)
                if (this.id == 'raw_index') { this.innerHTML = order[this.id]}
                if (this.id == 'cost') { this.innerHTML = order[this.id]}
                if (this.id == 'cost_ruble') { this.innerHTML = order[this.id]}
                if (this.id == 'delivery_date') { this.innerHTML = order[this.id]}
            })
        })
    }

    async function init_update_page() {
        console.log('нууу')
        let sheet = await status_request()
        md5 = sheet['md5']
        if (md5 == current_sheet_md5) {
            await update_page()
        }
    }

    async function start(){
        await StatusRequest()}

window.addEventListener('load', (event) => {
   // let orders_on_page = $()
  //  check_status();
})



