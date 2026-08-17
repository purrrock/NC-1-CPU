#include <stdio.h>
#include <stdbool.h>

#include "../core/nc1_registers.h"

static int failures = 0;

#define CHECK(condition)                                                   \
    do                                                                     \
    {                                                                      \
        if (!(condition))                                                  \
        {                                                                  \
            printf("FAIL: %s (line %d)\n", #condition, __LINE__);          \
            failures++;                                                    \
        }                                                                  \
    } while (0)


static void pcl_callback(void *context)
{
    bool *called = (bool *)context;
    *called = true;
}


static void test_reset(void)
{
    nc1_register_file_t rf = {0};

    nc1_registers_reset(&rf);

    CHECK(nc1_get_a(&rf) == 0);
    CHECK(nc1_get_b(&rf) == 0);
    CHECK(nc1_get_x(&rf) == 0);
    CHECK(nc1_get_y(&rf) == 0);

    CHECK(nc1_get_sp(&rf) == 0x0F);

    /*
     * После reset M=1.
     * Z и C должны быть сброшены.
     */
    CHECK(nc1_get_fl(&rf) == NC1_FLAG_M);

    CHECK(nc1_get_pch(&rf) == 0);
    CHECK(nc1_get_pcl(&rf) == 0);
    CHECK(nc1_get_pc(&rf) == 0);
}


static void test_nibble_masking(void)
{
    nc1_register_file_t rf = {0};

    nc1_registers_reset(&rf);

    nc1_set_a(&rf, 0x1F);
    nc1_set_b(&rf, 0xAB);
    nc1_set_x(&rf, 0xF2);

    CHECK(nc1_get_a(&rf) == 0x0F);
    CHECK(nc1_get_b(&rf) == 0x0B);
    CHECK(nc1_get_x(&rf) == 0x02);
}


static void test_pc(void)
{
    nc1_register_file_t rf = {0};

    nc1_registers_reset(&rf);

    nc1_set_pc(&rf, 0xAB);

    CHECK(nc1_get_pch(&rf) == 0x0A);
    CHECK(nc1_get_pcl(&rf) == 0x0B);
    CHECK(nc1_get_pc(&rf) == 0xAB);
}


static void test_addr(void)
{
    nc1_register_file_t rf = {0};

    nc1_registers_reset(&rf);

    nc1_set_addr(&rf, 0xCD);

    CHECK(nc1_get_x(&rf) == 0x0C);
    CHECK(nc1_get_y(&rf) == 0x0D);
    CHECK(nc1_get_addr(&rf) == 0xCD);
}


static void test_flags(void)
{
    nc1_register_file_t rf = {0};

    nc1_registers_reset(&rf);

    CHECK(nc1_get_flag_z(&rf) == false);
    CHECK(nc1_get_flag_c(&rf) == false);
    CHECK(nc1_get_flag_m(&rf) == true);
    CHECK(nc1_get_flag_r(&rf) == false);

    nc1_set_flag_z(&rf, true);
    nc1_set_flag_c(&rf, true);
    nc1_set_flag_m(&rf, false);
    nc1_set_flag_r(&rf, true);

    CHECK(nc1_get_flag_z(&rf) == true);
    CHECK(nc1_get_flag_c(&rf) == true);
    CHECK(nc1_get_flag_m(&rf) == false);
    CHECK(nc1_get_flag_r(&rf) == true);

    /*
     * FL хранит все четыре бита, но generic read(FL)
     * по поведению Python возвращает только Z/C/M.
     */
    CHECK(nc1_get_fl(&rf) == 0x0B);
    CHECK(nc1_register_read(&rf, NC1_REG_FL) == 0x03);
}


static void test_register_read_write(void)
{
    nc1_register_file_t rf = {0};

    nc1_registers_reset(&rf);

    nc1_register_write(&rf, NC1_REG_A, 0x17);

    CHECK(nc1_register_read(&rf, NC1_REG_A) == 0x07);

    /*
     * Register ID также маскируется до трёх бит.
     * 0x08 -> register 0 (A).
     */
    nc1_register_write(&rf, 0x08, 0x05);

    CHECK(nc1_get_a(&rf) == 0x05);
}


static void test_pcl_callback(void)
{
    nc1_register_file_t rf = {0};
    bool callback_called = false;

    nc1_registers_reset(&rf);

    nc1_registers_set_pcl_callback(
        &rf,
        pcl_callback,
        &callback_called
    );

    CHECK(callback_called == false);

    nc1_set_pcl(&rf, 0x07);

    CHECK(callback_called == true);
    CHECK(nc1_get_pcl(&rf) == 0x07);
}


int main(void)
{
    printf("NC-1 Register File tests\n");
    printf("========================\n");

    test_reset();
    test_nibble_masking();
    test_pc();
    test_addr();
    test_flags();
    test_register_read_write();
    test_pcl_callback();

    if (failures == 0)
    {
        printf("\nALL TESTS PASSED\n");
        return 0;
    }

    printf("\nTESTS FAILED: %d\n", failures);
    return 1;
}